import datetime as dt
import re

from blocks import read_json
from settings import set_logger


logger = set_logger(__name__)


# TODO: チュートリアルの関数なので将来的に削除する
def update_home_tab(client, event, logger):
    logger.info("open")
    blocks = read_json("home.json")
    blocks[0]["text"]["text"] = str(dt.datetime.now())
    try:
        client.views_publish(
            user_id=event["user"],
            view={
                "type": "home",
                "callback_id": "home_view",
                "blocks": blocks
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


def register(app):
    logger.info("register")
    app.event("app_home_opened")(update_home_tab)
