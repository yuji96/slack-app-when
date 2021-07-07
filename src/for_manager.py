from slack_bolt import Ack
from slack_sdk import WebClient

from blocks import read_json
from settings import set_logger


logger = set_logger(__name__)


# TODO: チュートリアルの関数なので将来的に削除する
def open_modal_test(ack: Ack, body: dict, client: WebClient):
    ack()
    client.views_open(trigger_id=body["trigger_id"],
                      view=read_json("modal.json"))


def register(app):
    logger.info("register")
    app.shortcut("test")(open_modal_test)
