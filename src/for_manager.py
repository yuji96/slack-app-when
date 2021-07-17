from datetime import datetime, timedelta

from slack_bolt import Ack
from slack_sdk import WebClient

from blocks import read_json
from settings import set_logger

# TODO: デバッグ用で開発後には削除する
from pprint import pprint

logger = set_logger(__name__)


def home_tab(client, event, logger):
    """アプリホームビューを編集する．"""

    view_json = read_json("./statics/home.json")
    client.views_publish(user_id=event["user"],
                         view=view_json)


def set_schedule(ack: Ack, body: dict, client: WebClient, view: dict):
    """日程調整用 Modal を表示する．"""

    # アプリのホームタブから
    if "actions" in body:
        target = body["actions"][0]["value"]

    # ショートカットから
    else:
        target = body["callback_id"].removeprefix("set_schedules_")

    read_file = f"./modals/set_schedules-{target}.json"
    view_json = read_json(read_file)

    # 開始日を「今日」に、終了日を「明日」に設定
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    view_json["blocks"][1]['accessory']['initial_date'] = str(today.date())
    view_json["blocks"][2]['accessory']['initial_date'] = str(tomorrow.date())

    ack()
    client.views_open(trigger_id=body["trigger_id"],
                      view=view_json)


def update_schedule(ack: Ack, body: dict, client: WebClient):
    """日程調整用 Modal の内容を更新する．"""

    view_json = read_json("./modals/set_schedule.json")
    view_json["blocks"] = body["view"]["blocks"]

    ack()
    client.views_update(view=view_json,
                        hash=body["view"]["hash"],
                        view_id=body["view"]["id"])


def check_users(ack: Ack, body: dict, client: WebClient, view: dict):
    """日程調整用 Modal の提出を処理する．"""

    values = view["state"]["values"]
    modal_inputs = get_modal_inputs(body, values)
    modal_inputs["send_lists"] = values["users_select"]["multi_users_select-action"]["selected_users"]

    send_message(ack, modal_inputs, client)


def check_channels(ack: Ack, body: dict, client: WebClient, view: dict):

    values = view["state"]["values"]
    modal_inputs = get_modal_inputs(body, values)
    modal_inputs["send_lists"] = [list(values["channel_select"].values())[0]["selected_channel"]]

    send_message(ack, modal_inputs, client)


def get_modal_inputs(body: dict, values: dict):

    start_date = values["start_date"]["datepicker-action"]["selected_date"]
    end_date = values["end_date"]["datepicker-action"]["selected_date"]
    start_time = values["start_time"]["timepicker-action"]["selected_time"]
    end_time = values["end_time"]["timepicker-action"]["selected_time"]
    modal_inputs = {
        "host": "<@"+body["user"]["id"]+">",
        "date": start_date + " から " + end_date,
        "time": start_time + " から " + end_time,
        "setting": values["display_result"]["result-option"]["selected_option"]["text"]["text"]
    }

    return modal_inputs


def send_message(ack: Ack, inputs: dict, client: WebClient):

    ack()

    message_json = read_json("./statics/request_message.json")

    for item in message_json:
        if "block_id" in item:
            item["text"]["text"] += inputs[item["block_id"]]

    # 選択したユーザ・チャンネルにメッセージを投稿する

    for item in inputs["send_lists"]:
        client.chat_postMessage(channel=item,
                                text="メッセージを確認してください",
                                blocks=message_json)


def register(app):
    logger.info("register")

    # アプリのタブ イベント
    app.event("app_home_opened")(home_tab)

    # アプリのタブ内 モーダル発動 イベント
    app.action("set_schedules_channel")(set_schedule)
    app.action("set_schedules_im")(set_schedule)

    # ショートカット モーダル発動 イベント
    app.shortcut("set_schedules_channel")(set_schedule)
    app.shortcut("set_schedules_im")(set_schedule)

    # モーダル入力時
    app.action("datepicker-action")(update_schedule)
    app.action("multi_conversations_select-action")(update_schedule)
    app.action("result-option")(update_schedule)

    # モーダル提出時
    app.view("set_schedules-im")(check_users)
    app.view("set_schedules-channel")(check_channels)
