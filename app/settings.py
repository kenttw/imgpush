import os

IMAGES_DIR = "/images/"
CACHE_DIR  = "/cache/"
OUTPUT_TYPE = None
MAX_UPLOADS_PER_DAY = 100000
MAX_UPLOADS_PER_HOUR = 100000
MAX_UPLOADS_PER_MINUTE = 100000
ALLOWED_ORIGINS = ["*"]
IMAGE_TYPES = ["png", 'jpeg', 'jpg', 'gif', ]
FILE_TYPES = ['zip', 'xlsx']

NAME_STRATEGY = "randomstr"
MAX_TMP_FILE_AGE = 5 * 60
RESIZE_TIMEOUT = 5
NUDE_FILTER_MAX_THRESHOLD = None
ALLOW_FILE_TYPES = ['xlsx', 'xls', 'txt', 'zip']

VALID_SIZES = []

MAX_SIZE_MB = 16

for variable in [item for item in globals() if not item.startswith("__")]:
    NULL = "NULL"
    env_var = os.getenv(variable, NULL).strip()
    if env_var is not NULL:
        try:
            env_var = eval(env_var)
        except Exception:
            pass
    globals()[variable] = env_var if env_var is not NULL else globals()[variable]
