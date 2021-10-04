""" This module provides basic helper functions that facilitate testing.
"""

import string
import random
import os


def random_string(length):
    return "".join(random.choice(string.ascii_letters) for _ in range(length))


def random_hex_string(length):
    return "".join(random.choice(string.hexdigits) for _ in range(length))


def clean_file(path):
    try:
        os.unlink(path)
    except OSError:
        pass
