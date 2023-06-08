import filetype

def test_file2url():
    """
    upload a image to generate a temporary url for quickly review
    """
    import requests

    fr = open('./dog.jpg', 'rb')
    data = fr.read()
    files = {'file':data}
    hosturl = 'http://127.0.0.1:5000/'
    r = requests.post(hosturl, files=files)

    new_url = hosturl + r.json()['filename']
    return new_url

def test_file():
    ext = filetype.guess_extension("test.py")
    print(ext)

