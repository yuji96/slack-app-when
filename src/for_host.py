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


def open_modal(ack: Ack, body: dict, client: WebClient, view: dict):
    """日程調整用 Modal を表示する．"""

    view_json = read_json("./modals/set_schedules.json")

    if "actions" in body:                   # アプリのホームタブから
        target_id = body["actions"][0]["action_id"]
        target = body["actions"][0]["value"]
    else:                                   # ショートカットから
        target_id = body["callback_id"]
        target = target_id.removeprefix("set_schedules-")

    view_json["callback_id"] = target_id
    view_json["blocks"]=insert_block(target)
    
    ack()
    client.views_open(trigger_id=body["trigger_id"],
                      view=view_json)


def insert_block(target: str):

    insert_blocks = []
    directory = "./set"

    # 開始日を「今日」に、終了日を「明日」に設定
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    date_json=read_json(f"{directory}/set_date.json")
    date_json[1]['accessory']['initial_date'] = str(today.date())
    date_json[2]['accessory']['initial_date'] = str(tomorrow.date())
    insert_blocks.extend(date_json)

    time_json = read_json(f"{directory}/set_time.json")
    insert_blocks.extend(time_json)

    target_json = read_json(f"{directory}/set_{target}.json")
    insert_blocks.extend(target_json)

    display_json = read_json(f"{directory}/set_display.json")
    insert_blocks.extend(display_json)

    return insert_blocks


def update_modal(ack: Ack, body: dict, client: WebClient):
    """日程調整用 Modal の内容を更新する．"""

    view_json = read_json("./modals/set_schedules.json")
    view_json["blocks"] = body["view"]["blocks"]
    view_json["callback_id"] = body["view"]["callback_id"]

    #TODO: 入力した時間と日程が有効かどうか確認する

    ack()
    client.views_update(view=view_json,
                        hash=body["view"]["hash"],
                        view_id=body["view"]["id"])

def check_modal(ack: Ack, body: dict, client: WebClient, view: dict):

    values = view["state"]["values"]
    modal_inputs = get_modal_inputs(body, values)

    target = body["view"]["callback_id"]
    if target == 'set_schedules-im':
        modal_inputs["send_lists"] = check_users(values)
    elif target == 'set_schedules-channel':
        modal_inputs["send_lists"] = check_channels(values)

    ack()
    send_message(modal_inputs, client)

def check_users(values):
    return values["users_select"]["multi_users_select-action"]["selected_users"]

def check_channels(values):
    return [list(values["channel_select"].values())[0]["selected_channel"]]

def get_modal_inputs(body: dict, values: dict):

    start_date = values["start_date"]["host_datepicker-action"]["selected_date"]
    end_date = values["end_date"]["host_datepicker-action"]["selected_date"]
    start_time = values["start_time"]["host_timepicker-action"]["selected_time"]
    end_time = values["end_time"]["host_timepicker-action"]["selected_time"]
    setting = values["display_result"]["result-option"]["selected_option"]["text"]["text"]
    modal_inputs = {
        "host" : "<@"+body["user"]["id"]+">",
        "date" : start_date + " から " + end_date,
        "time" : start_time + " から " + end_time,
        "setting" : setting,
        "start_date" : start_date,
        "end_date" : end_date,
        "start_time" : start_time,
        "end_time" : end_time
    }

    return modal_inputs


def send_message(inputs: dict, client: WebClient):

    message_json = read_json("./message/from_host.json")

    for item in message_json:
        if "block_id" in item:
            item["text"]["text"]+=inputs[item["block_id"]]
    
    # 選択したユーザ・チャンネルにメッセージを投稿する
    for item in inputs["send_lists"]:
        client.chat_postMessage(channel=item,
                                text="メッセージを確認してください",
                                blocks=message_json,
                                as_user=True)


def register(app):
    logger.info("register")

    # アプリのタブ イベント
    app.event("app_home_opened")(home_tab)

    # アプリのタブ内 モーダル発動 イベント
    app.action("set_schedules-channel")(open_modal)
    app.action("set_schedules-im")(open_modal)

    # ショートカット モーダル発動 イベント
    app.shortcut("set_schedules-channel")(open_modal)
    app.shortcut("set_schedules-im")(open_modal)

    # モーダル入力時
    app.action("host_datepicker-action")(update_modal)
    app.action("host_timepicker-action")(update_modal)

    # モーダル提出時
    app.view("set_schedules-im")(check_modal)
    app.view("set_schedules-channel")(check_modal)
