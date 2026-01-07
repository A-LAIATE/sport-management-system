import os

TESTING = False
DEBUG = False
# This is the DEV secret, when we release
SECRET_KEY = os.getenv("SECRET_KEY")
if SECRET_KEY is None:
    raise ValueError(
        "The environment variable 'SECRET_KEY' is not set. Please set it - check the README for more"
    )
