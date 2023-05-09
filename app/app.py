import datetime
import hashlib
import time
import glob
import os
import random
import shutil
import string
import urllib.request
import uuid

import filetype
import timeout_decorator
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
# from wand.exceptions import MissingDelegateError
# from wand.image import Image
from werkzeug.middleware.proxy_fix import ProxyFix
from PIL import Image

import settings

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

CORS(app, origins=settings.ALLOWED_ORIGINS)
app.config["MAX_CONTENT_LENGTH"] = settings.MAX_SIZE_MB * 1024 * 1024
limiter = Limiter(app, key_func=get_remote_address, default_limits=[])

app.use_x_sendfile = True


if settings.NUDE_FILTER_MAX_THRESHOLD:
    from nudenet import NudeClassifier
    nude_classifier = NudeClassifier()
else:
    nude_classifier = None


# @app.after_request
# def after_request(resp):
#     x_sendfile = resp.headers.get("X-Sendfile")
#     if x_sendfile:
#         resp.headers["X-Accel-Redirect"] = "/nginx/" + x_sendfile
#         del resp.headers["X-Sendfile"]
#     resp.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
#     return resp


class InvalidSize(Exception):
    pass


class CollisionError(Exception):
    pass


def _get_size_from_string(size):
    try:
        size = int(size)
        if len(settings.VALID_SIZES) and size not in settings.VALID_SIZES:
            raise InvalidSize
    except ValueError:
        size = ""
    return size


def _clear_imagemagick_temp_files():
    """
    A bit of a hacky solution to prevent exhausting the cache ImageMagick uses on disk.
    It works by checking for imagemagick cache files under /tmp/
    and removes those that are older than settings.MAX_TMP_FILE_AGE in seconds.
    """
    imagemagick_temp_files = glob.glob("/tmp/magick-*")
    for filepath in imagemagick_temp_files:
        modified = datetime.datetime.strptime(
            time.ctime(os.path.getmtime(filepath)), "%a %b %d %H:%M:%S %Y",
        )
        diff = datetime.datetime.now() - modified
        seconds = diff.seconds
        if seconds > settings.MAX_TMP_FILE_AGE:
            os.remove(filepath)


def _get_random_filename():
    random_string = _generate_random_filename()
    if settings.NAME_STRATEGY == "randomstr":
        file_exists = len(glob.glob(f"{settings.IMAGES_DIR}/{random_string}.*")) > 0
        if file_exists:
            return _get_random_filename()
    return random_string


def _generate_random_filename():
    if settings.NAME_STRATEGY == "uuidv4":
        return str(uuid.uuid4())
    if settings.NAME_STRATEGY == "randomstr":
        return "".join(
            random.choices(
                string.ascii_lowercase + string.digits + string.ascii_uppercase, k=5
            )
        )


def _resize_image(path, width, height):
    filename_without_extension, extension = os.path.splitext(path)

    # with Image.op(filename=path) as src:
    #     img = src.clone()

    img: Image = Image.open(path)


    current_aspect_ratio = img.width / img.height

    if not width:
        width = int(current_aspect_ratio * height)

    if not height:
        height = int(width / current_aspect_ratio)

    desired_aspect_ratio = width / height

    # Crop the image to fit the desired AR

    img = img.resize([width,height])
    return img

    # @timeout_decorator.timeout(settings.RESIZE_TIMEOUT)
    # def resize(img, width, height):
    #     img.sample(width, height)
    #
    # try:
    #     resize(img, width, height)
    # except timeout_decorator.TimeoutError:
    #     pass
    #
    # return img


@app.route("/", methods=["GET"])
def root():
    return """
<form action="/" method="post" enctype="multipart/form-data">
    <input type="file" name="file" id="file">
    <input type="submit" value="Upload" name="submit">
</form>
"""


@app.route("/liveness", methods=["GET"])
def liveness():
    return Response(status=200)


@app.route("/", methods=["POST"])
@limiter.limit(
    "".join(
        [
            f"{settings.MAX_UPLOADS_PER_DAY}/day;",
            f"{settings.MAX_UPLOADS_PER_HOUR}/hour;",
            f"{settings.MAX_UPLOADS_PER_MINUTE}/minute",
        ]
    )
)
def upload_image():
    _clear_imagemagick_temp_files()

    random_string = _get_random_filename()
    tmp_filepath = os.path.join("/tmp/", random_string)

    if "file" in request.files:
        file = request.files["file"]
        file.save(tmp_filepath)
    elif "url" in request.json:
        urllib.request.urlretrieve(request.json["url"], tmp_filepath)
    else:
        return jsonify(error="File is missing!"), 400

    if settings.NUDE_FILTER_MAX_THRESHOLD:
        unsafe_val = nude_classifier.classify(tmp_filepath).get(tmp_filepath, dict()).get("unsafe", 0)
        if unsafe_val >= settings.NUDE_FILTER_MAX_THRESHOLD:
            os.remove(tmp_filepath)
            return jsonify(error="Nudity not allowed"), 400

    output_type = settings.OUTPUT_TYPE or filetype.guess_extension(tmp_filepath)
    error = None



    hash_md5 = hashlib.md5()
    with open(tmp_filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    md5_str = str(hash_md5.hexdigest())
    output_filename = f"{md5_str}.{output_type}"
    #output_filename = os.path.basename(tmp_filepath) + f".{output_type}"
    output_path = os.path.join(settings.IMAGES_DIR, output_filename)

    try:

        if os.path.exists(output_path):
            pass
        elif output_type in settings.IMAGE_TYPES:
            with Image.open(tmp_filepath) as img:
                img.save(output_path)
        elif output_type in settings.FILE_TYPES:
            shutil.move(tmp_filepath, output_path)

        else:
            return jsonify(error=f"not support {output_type}"), 400

    except Exception as e :
        return jsonify(error=str(e)), 400
    finally:
        if os.path.exists(tmp_filepath):
            os.remove(tmp_filepath)

    if error:
        return jsonify(error=error), 400

    return jsonify(filename=output_filename)
@app.route("/ii/")
def ii():
    return send_from_directory("/Users/kent/git/imgpush/cache/", 'Kf8CX_100x100..jpg', as_attachment=False, mimetype='image/generic')


@app.route("/<string:filename>", methods=['GET'])
def get_image(filename: str):
    file_type = filename.split(".")[-1]
    width = request.args.get("w", "")
    height = request.args.get("h", "")

    path = os.path.join(settings.IMAGES_DIR, filename)

    if file_type in settings.IMAGE_TYPES:

        if (width or height) and (os.path.isfile(path)):
            try:
                width = _get_size_from_string(width)
                height = _get_size_from_string(height)
            except InvalidSize:
                return (
                    jsonify(error=f"size value must be one of {settings.VALID_SIZES}"),
                    400,
                )

            filename_without_extension, extension = os.path.splitext(filename)
            dimensions = f"{width}x{height}"
            resized_filename = filename_without_extension + f"_{dimensions}.{extension}"

            resized_path = os.path.join(settings.CACHE_DIR, resized_filename)

            if not os.path.isfile(resized_path) and (width or height):
                _clear_imagemagick_temp_files()
                resized_image = _resize_image(path, width, height)
                resized_image.save(resized_path)
                del resized_image
            return send_from_directory(settings.CACHE_DIR, resized_filename, mimetype='image/generic', as_attachment=False)

        return send_from_directory(settings.IMAGES_DIR, filename, mimetype='image/generic', as_attachment=False)
    else:
        return send_from_directory(settings.IMAGES_DIR, filename, as_attachment=True)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)