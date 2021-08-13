from datetime import datetime, timedelta

from blocks.base import Action, Button, DatePicker, Header, Input, Modal, PlainTextInput, Section, TimePicker
from blocks import read_json


def message_from_host(host_id, start_date, end_date, start_time, end_time,
                      setting=None, *args, **kwargs):
    header = Header("時間調整のご協力")
    sections = [Section("以下の内容で時間調整を行います。"),
                Section(f"*主催者:*\n<@{host_id}>", block_id="host"),
                Section(f"*開催日:*\n{start_date} から {end_date}", block_id="date"),
                Section(f"*開催時間:*\n{start_time} から {end_time}", block_id="time")]
    action = Action(Button(action_id="answer_schedule", value="answer_schedule",
                           text="回答する", style="primary"),
                    Button(action_id="not_answer", value="answer_schedule",
                           text="不参加", style="danger"))
    if setting:
        sections.append(Section(f"*回答設定:*\n{setting}", block_id="setting"))
    return [header, *sections, action]


def modal_for_host(callback_id: str):
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    target = callback_id.removeprefix("set_schedules-")

    modal = Modal(callback_id=callback_id, title="時間調整", submit="送信する", blocks=[
        Header("開催したい日程"),
        Section("この日から", block_id="start_date",
                accessory=DatePicker(action_id="host_datepicker-action", initial=today.date())),
        Section("この日までの間に開催したい", block_id="end_date",
                accessory=DatePicker(action_id="host_datepicker-action", initial=tomorrow.date())),
        Header("開催可能な時間帯"),
        Section("この時刻から", block_id="start_time",
                accessory=TimePicker(action_id="host_timepicker-action", initial="06:00")),
        Section("この時刻まで", block_id="end_time",
                accessory=TimePicker(action_id="host_timepicker-action", initial="23:00"))
    ])
    modal["blocks"].extend(read_json(f"set/set_{target}.json"))  # TODO: remove json

    # チャンネル用の共有設定 のブロック
    if target == "channel":
        modal["blocks"].extend(read_json("set/set_display.json"))  # TODO: remove json

    return modal


def modal_for_member(callback_id, values):
    return Modal(callback_id=callback_id, title="When!", submit="送信する", blocks=[
        Header("日程調整の回答", block_id=values["host_info"])] + [
        Input(block_id=date, label=f"{date} の {values['time']}", optional=True,
              element=PlainTextInput(action_id="plain_text_input-action",
                                     initial="all",
                                     placeholder="例：1400-1500, 1730~1800 （空欄は終日不可能）"))
        for date in values["date"]
    ])
