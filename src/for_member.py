import re

import pandas as pd
from slack_bolt import Ack
from slack_sdk import WebClient

from blocks.builder import modal_for_member
from settings import set_logger
from visualize import Table

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

    date_range = pd.date_range(*re.findall(r"\d{4}-\d{2}-\d{2}", str(body))).date.astype(str)
    start_time, end_time = re.findall(r"\d{2}:\d{2}", str(body))
    host_info = body["actions"][0]["value"]

    client.views_open(trigger_id=body["trigger_id"],
                      view=modal_for_member("answer_schedule",
                                            date_range, start_time, end_time, host_info))


def recieve_answer(ack: Ack, body: dict, client: WebClient, view: dict):
    """回答用 Modal の提出を確認する．"""

    ack()

    # member = body["user"]["id"]
    header, *_ = filter(lambda b: b["type"] == "header", view["blocks"])
    host_channel, host_message_ts = header["block_id"].split("-")

    parent_message, *replies = client.conversations_replies(
        channel=host_channel, ts=host_message_ts)["messages"]
    team_id = parent_message["team"]
    bot_user_id = parent_message["user"]

    answer = {k: v["plain_text_input-action"]["value"]
              for k, v in view["state"]["values"].items()}
    _, input_, *_ = view["blocks"]
    start_date, *_, end_date = answer

    if not replies:
        # TODO: username と name の違いとは？ display name はとれない？
        table = Table(answer=answer, name=body["user"]["name"],
                      date_pair=(start_date, end_date),
                      time_pair=input_["element"]["initial_value"].split("-"),
                      client=client)
    else:
        bot_msg, *_ = [msg for msg in replies if msg["user"] == bot_user_id]
        old_pkl_id = bot_msg["files"][0]["title"]
        table = Table(answer=answer, name=body["user"]["name"],
                      date_pair=(start_date, end_date),
                      time_pair=input_["element"]["initial_value"].split("-"),
                      client=client,
                      file_url=f"https://files.slack.com/files-pri/{team_id}-{old_pkl_id}/download/table.pkl")

    new_pkl_id = table.upload(bot_user_id)
    client.files_upload(content=table.visualize(), filetype="png", title=new_pkl_id,
                        channels=host_channel, thread_ts=host_message_ts)

    # TODO: 更新した時に古いファイルを削除したい

def send_no_answer(ack: Ack, body: dict, client: WebClient):
    """参加できない と主催者に送信する．"""

    ack()

    member = body["user"]["id"]
    host_channel, host_message_ts = body["actions"][0]["value"].split('-')

    client.chat_postMessage(text=f"<@{member}> が「不参加」と回答しました。",
                            channel=host_channel,
                            thread_ts=host_message_ts,
                            as_user=True)
