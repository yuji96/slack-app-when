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

    option_json=read_json("./answer/add_option.json")
    option_json["value"] = body["actions"][-1]["value"]
    
    users_json=read_json("./answer/add_user.json")
    users_json[-1]["element"]["initial_option"]=option_json
    users_json[-1]["element"]["options"].append(option_json)

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
    targets = values["target_select"]["static_select-action"]["selected_option"]["value"]
    dates,date = {}, "date"

    date_list = sorted(list(values.keys()))[:-1]
    for item in date_list:

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
        "send_lists" : [targets],
        "available_date" : dates,
        "member" : body["user"]["id"]
    }


def get_message(value: str, client: WebClient):

    target_channel, host, post_time = value.split('-')

    # Target message
    message_list = client.conversations_history(
        channel = target_channel,
        oldest = post_time,
        inclusive = True,
        limit=1)["messages"]
    
    if message_list == []:
        return None

    message_info = message_list[0]
    target_message = message_info["ts"]

    # If Threads exist
    thread_present = False
    if "thread_ts" in message_info:
        thread_present = True

        reply_content = client.conversations_replies(
            channel = target_channel,
            ts = message_info["thread_ts"],
            )["messages"][-1]

        target_message = reply_content["ts"]
        message_content = reply_content["blocks"][0]["text"]["text"]

    return {
        "thread_present" : thread_present,
        "channel" : target_channel,
        "ts" : target_message,
        "message" :message_content,
    }


def check_modal(ack: Ack, body: dict, client: WebClient, view: dict):

    values = view["state"]["values"]
    inputs = get_modal_inputs(body,values)

    ack()    
    secret_value = values["target_select"]["static_select-action"]["selected_option"]["value"]
    send_answer(inputs,secret_value,client)


def send_answer(inputs: dict, secret_value: str, client: WebClient):
    
    result = get_message(secret_value,client)

    message_json = read_json("./message/from_member-yes.json")
    message_json[0]["text"]["text"] = message_json[0]["text"]["text"].replace("I",f"<@{inputs['member']}>")

    if result["thread_present"]:
        message_json[0]["text"]["text"] += f"\n{result['message']}"
    
    send_host(
        thread=result["thread_present"],
        target_channel=result["channel"],
        target_message=result["ts"],
        input_block=message_json,
        client=client
    )

    # モーダルの入力を表示する
    print(f"\n\nモーダルの入力")
    pprint({"result" : inputs['available_date']})


def send_not_answer(ack: Ack, body: dict, client: WebClient):

    member = body["user"]["id"]
    secret_value = body["actions"][0]["value"]
    result = get_message(secret_value, client)

    message_json = read_json("./message/from_member-no.json")
    message_json[0]["text"]["text"] = message_json[0]["text"]["text"].replace("I",f"<@{member}>")
    
    if result["thread_present"]:
        message_json[0]["text"]["text"] += f"\n{result['message']}"
    
    ack()
    send_host(
        thread=result["thread_present"],
        target_channel=result["channel"],
        target_message=result["ts"],
        input_block=message_json,
        client=client
    )


def send_host(thread: bool, target_channel: str, target_message: str, input_block: dict, client: WebClient):

    if thread:
        client.chat_update(
            channel = target_channel,
            text = "メッセージを確認してください",
            blocks = input_block,
            ts = target_message,
            as_user = True)
    else:
        client.chat_postMessage(
            channel = target_channel,
            text = "メッセージを確認してください",
            blocks = input_block,
            thread_ts = target_message,
            as_user = True)


def register(app):
    logger.info("register")
    
    # メッセージのクリック時
    app.action("answer_schedule")(open_modal)
    app.action("not_answer")(send_not_answer)

    # 「追加」ボタンのクリック時
    app.action("member-add_date")(update_modal)

    # 時間の選択時
    app.action("member_start-timepicker-action")(update_modal)
    app.action("member_end-timepicker-action")(update_modal)
    app.action("member_check-action")(update_modal)

    # 提出時
    app.view("answer_schedule")(check_modal)