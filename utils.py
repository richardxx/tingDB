__author__ = 'richardxx'

import base64
import hashlib


def encrypt_string(str):
    md5 = hashlib.md5()
    md5.update(str)
    return base64.b32encode(md5.digest())

