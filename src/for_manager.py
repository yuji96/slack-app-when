""" スケジュール調整を主催する為の機能 """

from datetime import datetime, timedelta

from slack_bolt import Ack
from slack_sdk import WebClient

from blocks import read_json
from settings import set_logger


logger = set_logger(__name__)


def home_tab(client: WebClient, event: dict) -> dict:
    """アプリホームビューを編集する．"""
    client.views_publish(user_id=event["user"],
                         view=read_json("./app_tab/home.json"))


def open_modal(ack: Ack, body: dict, client: WebClient, view: dict) -> dict:
    """日程調整用 Modal を表示する．"""
    view_json = read_json("./modals/set_schedules.json")

    if "actions" in body:
        # アプリホームビュー から
        target_id = str(body["actions"][0]["action_id"])
    else:
        # ショートカット から
        target_id = str(body["callback_id"])
    view_json["callback_id"] = target_id
    target = target_id.removeprefix("set_schedules-")

    # モーダルのブロック を追加
    view_json["blocks"] = insert_block(target)

    ack()

    # モーダルを開く
    client.views_open(
        trigger_id=body["trigger_id"],
        view=view_json)


def insert_block(target: str) -> list:
    """日程調整用 Modal のブロックを追加する．"""

    insert_blocks = []

    # 日程調整用 Modal ブロックのディレクトリ
    directory = "./set"

    # 日程選択 のブロック
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    date_json = read_json(f"{directory}/set_date.json")

    # 開始日 ->「今日」、終了日 ->「明日」 に設定
    date_json[1]['accessory']['initial_date'] = str(today.date())
    date_json[2]['accessory']['initial_date'] = str(tomorrow.date())

    insert_blocks.extend(date_json)

    # 時間選択 のブロック
    time_json = read_json(f"{directory}/set_time.json")
    insert_blocks.extend(time_json)

    # 回答者選択 のブロック
    target_json = read_json(f"{directory}/set_{target}.json")
    insert_blocks.extend(target_json)

    # チャンネル用の共有設定 のブロック
    if target == "channel":
        display_json = read_json(f"{directory}/set_display.json")
        insert_blocks.extend(display_json)

    return insert_blocks


def update_modal(ack: Ack, body: dict, client: WebClient):
    """日程調整用 Modal の内容を更新する．"""

    view_json = read_json("./modals/set_schedules.json")

    # 更新する内容
    view_json["blocks"] = body["view"]["blocks"]
    view_json["callback_id"] = body["view"]["callback_id"]

    # TODO: 入力した時間と日程が有効かどうか確認する

    ack()

    # モーダルを更新する
    client.views_update(
        view=view_json,
        hash=body["view"]["hash"],
        view_id=body["view"]["id"])


def check_users(values: dict) -> list:
    """日程調整用 Modal の「回答者」の欄の ユーザー を取得する．"""

    return values["users_select"]["multi_users_select-action"]["selected_users"]


def check_channels(values: dict) -> list:
    """日程調整用 Modal の「回答者」の欄の チャンネル を取得する．"""

    return [list(values["channel_select"].values())[0]["selected_channel"]]


def get_modal_inputs(body: dict, values: dict) -> dict:
    """日程調整用 Modal の入力を取得する．"""

    # 日付
    start_date = values["start_date"]["host_datepicker-action"]["selected_date"]
    end_date = values["end_date"]["host_datepicker-action"]["selected_date"]

    # 時間
    start_time = values["start_time"]["host_timepicker-action"]["selected_time"]
    end_time = values["end_time"]["host_timepicker-action"]["selected_time"]

    modal_inputs = {
        "host": "<@"+body["user"]["id"]+">",
        "host_id": body["user"]["id"],
        "date": start_date + " から " + end_date,
        "time": start_time + " から " + end_time,
        "start_date": start_date,
        "end_date": end_date,
        "start_time": start_time,
        "end_time": end_time
    }

    # チャンネル用　の回答共有設定
    if "display_result" in values:
        setting = values["display_result"]["result-option"]["selected_option"]
        modal_inputs["setting"] = setting["text"]["text"]
        modal_inputs["setting_value"] = setting["value"]

    return modal_inputs


def check_modal(ack: Ack, body: dict, client: WebClient, view: dict):
    """日程調整用 Modal の提出を確認する．"""

    values = view["state"]["values"]

    # モーダルの入力値を取得
    modal_inputs = get_modal_inputs(body, values)

    # チャンネル・個人用 の確認
    target = body["view"]["callback_id"]
    if target == 'set_schedules-im':
        modal_inputs["send_lists"] = get_users(values)
    elif target == 'set_schedules-channel':
        modal_inputs["send_lists"] = get_channels(values)

    ack()

    # メッセージを送信
    send_message(modal_inputs, client)


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


def send_message(inputs: dict, client: WebClient):
    """選択した回答者宛に メッセージ を送る．"""

    # 回答者宛のメッセージブロック
    message_json = read_json("./message/from_host.json")

    for item in message_json:
        if "block_id" in item:
            if item["block_id"] not in inputs:
                message_json.remove(item)
            else:
                item["text"]["text"] += inputs[item["block_id"]]

    # 主催者用の　スケジュール調整の詳細ブロック
    detail_json = read_json("./message/schedule_detail.json")
    detail_json.extend(message_json[3:-1])

    # 主催者 に作成した調整を送信する
    response = client.chat_postMessage(channel=inputs["host_id"],
                                       text="メッセージを確認してください",
                                       blocks=detail_json,
                                       as_user=True)

    # 主催者と主催メッセージの情報を追加する
    message_json[-1]["elements"][0]["value"] = f"{response['channel']}-{inputs['host_id']}-{response['ts']}"
    message_json[-1]["elements"][1]["value"] = f"{response['channel']}-{inputs['host_id']}-{response['ts']}"

    # 選択したユーザ・チャンネル にメッセージを送信する
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


##########################################
# utilities
##########################################


def build_schedule_block(target: str) -> list:
    """日程調整用 Modal のブロックを追加する．"""

    insert_blocks = []

    # 日程調整用 Modal ブロックのディレクトリ
    directory = "./set"

    # 日程選択 のブロック
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    date_json = read_json(f"{directory}/set_date.json")

    # 開始日 ->「今日」、終了日 ->「明日」 に設定
    date_json[1]['accessory']['initial_date'] = str(today.date())
    date_json[2]['accessory']['initial_date'] = str(tomorrow.date())

    insert_blocks.extend(date_json)

    # 時間選択 のブロック
    time_json = read_json(f"{directory}/set_time.json")
    insert_blocks.extend(time_json)

    # 回答者選択 のブロック
    target_json = read_json(f"{directory}/set_{target}.json")
    insert_blocks.extend(target_json)

    # チャンネル用の共有設定 のブロック
    if target == "channel":
        display_json = read_json(f"{directory}/set_display.json")
        insert_blocks.extend(display_json)

    return insert_blocks


def get_users(values: dict) -> list:
    """日程調整用 Modal の「回答者」の欄の ユーザー を取得する．"""

    return values["users_select"]["multi_users_select-action"]["selected_users"]


def get_channels(values: dict) -> list:
    """日程調整用 Modal の「回答者」の欄の チャンネル を取得する．"""

    return [list(values["channel_select"].values())[0]["selected_channel"]]


def get_modal_inputs(body: dict, values: dict) -> dict:
    """日程調整用 Modal の入力を取得する．"""

    # 日付
    start_date = values["start_date"]["host_datepicker-action"]["selected_date"]
    end_date = values["end_date"]["host_datepicker-action"]["selected_date"]

    # 時間
    start_time = values["start_time"]["host_timepicker-action"]["selected_time"]
    end_time = values["end_time"]["host_timepicker-action"]["selected_time"]

    modal_inputs = {
        "host": "<@"+body["user"]["id"]+">",
        "host_id": body["user"]["id"],
        "date": start_date + " から " + end_date,
        "time": start_time + " から " + end_time,
        "start_date": start_date,
        "end_date": end_date,
        "start_time": start_time,
        "end_time": end_time
    }

    # チャンネル用　の回答共有設定
    if "display_result" in values:
        setting = values["display_result"]["result-option"]["selected_option"]
        modal_inputs["setting"] = setting["text"]["text"]
        modal_inputs["setting_value"] = setting["value"]

    return modal_inputs
