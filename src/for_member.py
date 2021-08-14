import re

import pandas as pd
from slack_bolt import Ack
from slack_sdk import WebClient

from blocks.builder import modal_for_member
from settings import set_logger

# TODO: デバッグ用で開発後には削除する
from pprint import pprint

from visualize import Table


logger = set_logger(__name__)


def register(app):
    logger.info("register")

    # メッセージのクリック時
    app.action("answer_schedule")(open_answer_modal)
    app.action("not_answer")(send_no_answer)

    # 提出時
    app.view("answer_schedule")(recieve_answer)


def open_answer_modal(ack: Ack, body: dict, client: WebClient):
    """回答用 Modal を表示する．"""
    ack()

    date_range = pd.date_range(*re.findall(r"\d{4}-\d{2}-\d{2}", str(body))).date.astype(str)
    start_time, end_time = re.findall(r"\d{2}:\d{2}", str(body))
    host_info = body["actions"][0]["value"]

    client.views_open(trigger_id=body["trigger_id"],
                      view=modal_for_member("answer_schedule",
                                            date_range, start_time, end_time, host_info))


def recieve_answer(ack: Ack, body: dict, client: WebClient, view: dict):
    """回答用 Modal の提出を確認する．"""

    ack()

    member = body["user"]["id"]
    header, *_ = filter(lambda b: b["type"] == "header", view["blocks"])
    host_channel, host_message_ts = header["block_id"].split("-")

    client.chat_postMessage(text=f"<@{member}> が日程を回答しました。",
                            channel=host_channel,
                            thread_ts=host_message_ts,
                            as_user=True)

    answer = {k: v["plain_text_input-action"]["value"] for k, v in view["state"]["values"].items()}
    header, input_, *_ = view["blocks"]
    start_date, *_, end_date = answer
    # TODO: username と name の違いとは？ display name はとれない？
    table = Table(answer=answer, name=body["user"]["name"],
                  date_pair=(start_date, end_date),
                  time_pair=input_["element"]["initial_value"].split("-"))
    print(table)

    # TODO:
    # host_message_ts を更新した画像を投稿
    # URLを埋め込む


def send_no_answer(ack: Ack, body: dict, client: WebClient):
    """参加できない と主催者に送信する．"""

    ack()

    member = body["user"]["id"]
    host_channel, host_message_ts = body["actions"][0]["value"].split('-')

    client.chat_postMessage(text=f"<@{member}> が「不参加」と回答しました。",
                            channel=host_channel,
                            thread_ts=host_message_ts,
                            as_user=True)
