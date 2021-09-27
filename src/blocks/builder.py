from datetime import datetime, timedelta

from blocks.base import (
    Actions, Button, ChannelsSelect, Datepicker, Header, Modal, PlainTextInput, RadioButtons,
    Section, Timepicker, MultiUsersSelect
)


def message_from_host(host_id, start_date, end_date, start_time, end_time,
                      setting=None, *args, **kwargs):
    header = Header("時間調整のご協力")
    sections = [Section("以下の内容で時間調整を行います。"),
                Section(f"*主催者:*\n<@{host_id}>", block_id="host"),
                Section(f"*開催日:*\n{start_date} から {end_date}", block_id="date"),
                Section(f"*開催時間:*\n{start_time} から {end_time}", block_id="time")]
    action = Actions(Button(action_id="answer_schedule", value="answer_schedule",
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

    # HACK: SectionではなくInputのDatepickerに置き換える
    modal = Modal(callback_id=callback_id, title="時間調整", submit="送信する", blocks=[
        Header("開催したい日程"),
        Section("この日から", block_id="start_date",
                accessory=Datepicker(action_id="host_datepicker-action", initial=today.date())),
        Section("この日までの間に開催したい", block_id="end_date",
                accessory=Datepicker(action_id="host_datepicker-action", initial=tomorrow.date())),
        Header("開催可能な時間帯"),
        Section("この時刻から", block_id="start_time",
                accessory=Timepicker(action_id="host_timepicker-action", initial="06:00")),
        Section("この時刻まで", block_id="end_time",
                accessory=Timepicker(action_id="host_timepicker-action", initial="23:00"))
    ])
    if target == "channel":
        modal["blocks"].extend([Header("回答チャンネル"),
                                ChannelsSelect(block_id="channel_select")])
    elif target == "im":
        modal["blocks"].extend([Header("回答者"),
                                MultiUsersSelect(block_id="users_select",
                                                 action_id="multi_users_select-action")])

    # チャンネル用の共有設定のブロック
    if target == "channel":
        modal["blocks"].extend([Header("回答の公開範囲"),
                                RadioButtons(block_id="display_result", action_id="result-option",
                                             options=[("主催者だけに回答を送る", "host"),
                                                      ("回答者に全員の回答を公開する", "all")])])

    return modal


def modal_for_member(callback_id, date_range, start_time, end_time, host_info):
    return Modal(callback_id=callback_id, title="When!", submit="送信する", blocks=[
        Header("日程調整の回答", block_id=host_info)] + [
        PlainTextInput(block_id=date, label=f"{date} の {start_time} から {end_time}",
                       action_id="plain_text_input-action",  optional=True,
                       initial=f"{start_time}-{end_time}",
                       placeholder="例：1400-1500, 1730~1800 （空欄は終日不可能）")
        for date in date_range
    ])
