import filetype

def test_file():
    ext = filetype.guess_extension("test.py")
    print(ext)