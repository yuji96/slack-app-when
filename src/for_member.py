import pandas as pd
from slack_bolt import Ack
from slack_sdk import WebClient

from blocks import read_json
from blocks.builder import modal_for_member
from settings import set_logger

# TODO: デバッグ用で開発後には削除する
from pprint import pprint


logger = set_logger(__name__)


def register(app):
    logger.info("register")

    # メッセージのクリック時
    app.action("answer_schedule")(open_modal)
    app.action("not_answer")(send_not_answer)

    # 提出時
    app.view("answer_schedule")(check_modal)


def open_modal(ack: Ack, body: dict, client: WebClient):
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

    client.views_open(trigger_id=body["trigger_id"],
                      view=modal_for_member(callback_id="answer_schedule", values=values))


def get_message(value: str, client: WebClient):
    """主催者の スケージュール調整詳細メッセージ を取得する"""

    target_channel, host, post_time = value.split('-')

    # Target message
    message_list = client.conversations_history(
        channel=target_channel,
        oldest=post_time,
        inclusive=True,
        limit=1)["messages"]

    if not message_list:
        return None

    message_info = message_list[0]
    target_message = message_info["ts"]

    result = {"channel": target_channel}

    # スレッドの確認
    thread_present = False
    if "thread_ts" in message_info:
        thread_present = True

        reply_content = client.conversations_replies(
            channel=target_channel,
            ts=message_info["thread_ts"],
            )["messages"][-1]

        target_message = reply_content["ts"]
        message_content = reply_content["blocks"][0]["text"]["text"]

        result["message"] = message_content

    result["thread_present"] = thread_present
    result["channel"] = target_channel
    result["ts"] = target_message

    return result


def check_modal(ack: Ack, body: dict, client: WebClient, view: dict):
    """回答用 Modal の提出を確認する．"""

    values = view["state"]["values"]
    inputs = get_modal_inputs(body, values)
    secret_value = inputs["secret_value"]

    ack()

    # メッセージを送信する
    send_answer(inputs, secret_value, client)


def send_answer(inputs: dict, secret_value: str, client: WebClient):
    """回答用 Modal の提出を確認メッセージを送信する．"""

    # スケジュール調整の詳細メッセージスレッドを取得
    result = get_message(secret_value, client)

    message_json = read_json("./message/from_member-yes.json")
    message_json[0]["text"]["text"] = message_json[0]["text"]["text"].replace("I", f"<@{inputs['member']}>")

    if result["thread_present"]:
        message_json[0]["text"]["text"] += f"\n{result['message']}"

    # 主催者にメッセージを送信する
    send_host(
        thread=result["thread_present"],
        target_channel=result["channel"],
        target_message=result["ts"],
        input_block=message_json,
        client=client
    )

    # モーダルの入力を表示する
    print("\n\nモーダルの入力")
    pprint({"result": inputs['available_date']})


def send_not_answer(ack: Ack, body: dict, client: WebClient):
    """参加できない と主催者に送信する．"""

    member = body["user"]["id"]
    secret_value = body["actions"][0]["value"]

    # スケジュール調整の詳細メッセージスレッドを取得
    result = get_message(secret_value, client)

    message_json = read_json("./message/from_member-no.json")
    message_json[0]["text"]["text"] = message_json[0]["text"]["text"].replace("I", f"<@{member}>")

    if result["thread_present"]:
        message_json[0]["text"]["text"] += f"\n{result['message']}"

    ack()

    # 主催者にメッセージを送信する
    send_host(
        thread=result["thread_present"],
        target_channel=result["channel"],
        target_message=result["ts"],
        input_block=message_json,
        client=client
    )


def send_host(thread: bool, target_channel: str, target_message: str, input_block: dict, client: WebClient):
    """ 主催者に送る """

    # スレッドの確認
    if thread:
        client.chat_update(
            channel=target_channel,
            text="メッセージを確認してください",
            blocks=input_block,
            ts=target_message,
            as_user=True)
    else:
        client.chat_postMessage(
            channel=target_channel,
            text="メッセージを確認してください",
            blocks=input_block,
            thread_ts=target_message,
            as_user=True)
