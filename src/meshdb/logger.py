import logging
import os


def configure():
    FORMAT = "[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s"
    logging.basicConfig(
        format=FORMAT,
        level=logging.DEBUG if os.environ.get("LOG_DEBUG") else logging.INFO,
    )
