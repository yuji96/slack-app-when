from logging import getLogger
import os
from os.path import join, dirname

import coloredlogs
from dotenv import load_dotenv


load_dotenv(join(dirname(__file__), '../.env'))
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
PORT = int(os.environ.get("PORT", 3000))


def set_logger(name, level="INFO"):
    logger = getLogger(name)
    logger.setLevel(level)
    coloredlogs.install(level=level, logger=logger)
    return logger
