import pandas as pd

from slack_bolt import Ack
from slack_sdk import WebClient

from blocks import read_json
from settings import set_logger

# TODO: デバッグ用で開発後には削除する
from pprint import pprint


logger = set_logger(__name__)


def open_modal(ack: Ack, body: dict, client: WebClient):

    view_json = read_json("./modals/answer_schedule.json")
    view_json["blocks"], time = insert_block(body)

    ack()
    client.views_open(
        trigger_id = body["trigger_id"],
        view = view_json)

def insert_block(body: dict) -> list:

    insert_blocks=[]
    values = {}

    items = [ 'host', 'date', 'time', 'setting' ]
    for item in body["message"]["blocks"] :
        if "block_id" in item and item["block_id"] in items:
            values[ item["block_id"] ] = item["text"]["text"].split("\n")[1]

    dates = values["date"].split(" から ")
    values["date"] = [ str(item.date()) for 
        item in list(pd.date_range(dates[0],dates[1])) ]

    for item in values["date"]:
        insert_blocks.extend(generate_block(item,values["time"],1))

    users_json=read_json("./answer/add_user.json")
    users_json[1]["element"]["initial_users"].append(body["user"]["id"])

    cond1 = body["channel"]["name"] != "directmessage"
    cond2 = body["actions"][0]["value"].removeprefix("answer_schedule-") != "host"
    if cond1 and cond2:
        users_json[1]["element"]["initial_users"].append(body["channel"]["id"])

    insert_blocks.extend(users_json)

    return insert_blocks, values["time"]


def generate_block(date: str, time: str, num: int) -> list:

    divider_block = {"type": "divider"}

    return [
        divider_block, 
        generate_date_block(date,time), 
        generate_time_block(date,time,num)
    ]


def generate_date_block(date: str,time: str) -> dict:

    date_block = read_json("./answer/add_date.json")
    date_block["block_id"] = date
    date_block["text"]["text"] = date_block["text"]["text"].replace("date",date).replace("time",time)
    date_block["accessory"]["value"] += f"-{date}"

    return date_block


def generate_time_block(date: str, time: str, num: int)  -> dict:

    start_time,end_time =  time.split(" から ")

    time_block = read_json("./answer/add_time.json")
    time_block["block_id"] = time_block["block_id"].replace("date",date).replace("opt",str(num))
    time_block["elements"][0]["initial_time"] = start_time
    time_block["elements"][1]["initial_time"] = end_time

    return time_block


def update_modal(ack: Ack, body: dict, client: WebClient):

    target_blocks = body["view"]["blocks"]
    action = body["actions"][0]["action_id"]

    if action == "member-add_date":
        target_blocks = update_option(body)
    else:
        target_blocks = update_time(body)

    view_json = read_json("./modals/answer_schedule.json")
    view_json["blocks"] = target_blocks

    ack()
    client.views_update(
        view = view_json,
        hash = body["view"]["hash"],
        view_id = body["view"]["id"])


def update_option(body: dict) -> dict:

    target_date = body["actions"][0]["block_id"]
    temp = body["view"]["blocks"]

    target_blocks = [ item for item in temp 
        if "block_id" in item and target_date in item["block_id"] ]

    option_num = len(target_blocks)
    option_time = str(target_blocks[0]["text"]["text"].split("の")[-1].strip(' *'))

    for i in range(len(temp)):
        if target_date in temp[i]["block_id"] :
                temp.insert(i+2,generate_time_block(target_date,option_time,option_num))
                break

    return temp


def update_time(body: dict) -> dict:

    #TODO:　入力した時間が有効か確認する
    #TODO:　重複しているか確認

    return body["view"]["blocks"]


def get_modal_inputs(body: dict, values: dict) -> dict:

    host = "<@" + body["user"]["id"] + ">"
    targets = values["target_select"]["multi_users_select-action"]["selected_users"]

    dates,date = {}, "date"
    for item in values:

        if item == "target_select":
            break

        temp = values[item]
        if date not in item:
            date = item[:-2]
            dates[date] = []

        if temp["member_check-action"]["selected_options"] is None:
            # TODO:終日用に設定する
            sets = []
        else:
            sets = [ temp["member_start-timepicker-action"]["selected_time"], 
                     temp["member_end-timepicker-action"]["selected_time"] ]

        dates[date].append(sets)

    return {
        "host" : host,
        "send_lists" : targets,
        "available_date" : dates
    }


def check_modal(ack: Ack, body: dict, client: WebClient, view: dict):

    values = view["state"]["values"]

    ack()
    send_message(ack, get_modal_inputs(body, values), client)


def send_message(ack: Ack, inputs: dict, client: WebClient):

    message_json = read_json("./message/from_member.json")

    #for item in message_json:
    #    if "block_id" in item:
    #        item["text"]["text"]+=inputs[item["block_id"]]

    # 選択したユーザ・チャンネルにメッセージを投稿する
    for item in inputs["send_lists"]:
        client.chat_postMessage(
            channel = item,
            text = "メッセージを確認してください",
            blocks = message_json,
            as_user = True)


def register(app):
    logger.info("register")
    
    # メッセージのクリック時
    app.action("answer_schedule")(open_modal)

    # 「追加」ボタンのクリック時
    app.action("member-add_date")(update_modal)

    # 時間の選択時
    app.action("member_start-timepicker-action")(update_modal)
    app.action("member_end-timepicker-action")(update_modal)
    app.action("member_check-action")(update_modal)

    # 提出時
    app.view("answer_schedule")(check_modal)
