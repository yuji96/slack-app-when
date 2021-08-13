import pandas as pd
from slack_bolt import Ack
from slack_sdk import WebClient

from blocks.builder import modal_for_member
from settings import set_logger

# TODO: デバッグ用で開発後には削除する
from pprint import pprint


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

    # [主催者、日、時間、設定] をメッセージから取得する
    values = {}
    items = ['host', 'date', 'time', 'setting']
    for item in body["message"]["blocks"]:
        if (block_id := item.get("block_id")) in items:
            values[block_id] = item["text"]["text"].split("\n")[1]

    start, end = values["date"].split(" から ")
    values["date"] = pd.date_range(start, end).date.astype(str)

    values["host_info"] = body["actions"][0]["value"]

    client.views_open(trigger_id=body["trigger_id"],
                      view=modal_for_member(callback_id="answer_schedule", values=values))


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

    # モーダルの入力を表示する
    print("\n\nモーダルの入力")
    values = view["state"]["values"]
    available_date = {item: values[item]["plain_text_input-action"]["value"]
                      for item in values}
    pprint({"result": available_date})

    # TODO: Table class のインスタンスを生成
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
