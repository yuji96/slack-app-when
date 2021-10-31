from logging import getLogger
import os
from os.path import join, dirname

import coloredlogs
from dotenv import load_dotenv


load_dotenv(join(dirname(__file__), '../.env'))
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
# TODO: よく考えたらワークスペースによって変わるから定数は無理
SLACK_BOT_ID = os.environ.get("SLACK_BOT_ID")
PORT = int(os.environ.get("PORT", 3000))
TMP_DIR = os.environ.get("TMP_DIR", join(dirname(__file__), './tmp/'))

# TODO: callback_id はすべてここで定義する。


def set_logger(name, level="INFO"):
    logger = getLogger(name)
    logger.setLevel(level)
    coloredlogs.install(level=level, logger=logger)
    return logger
