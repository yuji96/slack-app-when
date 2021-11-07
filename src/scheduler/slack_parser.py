import datetime as dt
import re


class SchedulerCreationFormData(dict):
    def __init__(self, body: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.body = body
        self.values_ = body["view"]["state"]["values"]
        self.set_modal_inputs()

    @property
    def members(self):
        return self.values_["users_select"]["multi_users_select-action"]["selected_users"]

    @property
    def channel(self) -> str:
        return self.values_["channel_select"]["channels_select-action"]["selected_channel"]

    def set_modal_inputs(self):
        values = self.values_
        self["start_date"] = values["start_date"]["host_datepicker-action"]["selected_date"]
        self["end_date"] = values["end_date"]["host_datepicker-action"]["selected_date"]
        self["start_time"] = values["start_time"]["host_timepicker-action"]["selected_time"]
        self["end_time"] = values["end_time"]["host_timepicker-action"]["selected_time"]
        self["host_id"] = self.body["user"]["id"]

        # チャンネル用 の回答共有設定
        if "display_result" in values:
            setting = values["display_result"]["result-option"]["selected_option"]
            self["setting"] = setting["text"]["text"]
            self["setting_value"] = setting["value"]


class AnswerFormData:
    def __init__(self, view=None,
                 answer=None, date_pair=None, time_pair=None):
        if view:
            answer_dict = {k: v["plain_text_input-action"]["value"]
                           for k, v in view["state"]["values"].items()}
            start_date, *_, end_date = answer_dict
            _, input_, *_ = view["blocks"]

        self._answer = answer or answer_dict
        self._date_pair = date_pair or (start_date, end_date)
        self._time_pair = time_pair or input_["element"]["initial_value"].split("-")
        self.slots = list(self.generate_slots())

    def generate_slots(self):
        def to_datetime(date: str, str_time: str) -> dt.datetime:
            if len(str_time) <= 2:
                format = "%H"
            elif ":" in str_time:
                format = "%H:%M"
            else:
                format = "%H%M"
            try:
                time = dt.datetime.strptime(str_time, format).time()
            except ValueError:
                raise AnswerFormException({date: f"`{str_time}` は24時間表記の時刻ではありません。"})
            date = dt.datetime.strptime(date, "%Y-%m-%d").date()
            return dt.datetime.combine(date, time)

        for date, text in self._answer.items():
            # TODO: 半角に変換
            if text is None:
                continue

            text = re.sub(r"\s*([:\-~,])\s*", r"\1", text)
            str_slots = text.split(",")
            # TODO: 末尾に変な文字が入ったら除去
            # HACK: そもそも削るんじゃなくて抽出する実装のほうがきれい

            for str_start, str_end in map(lambda slot: re.split(r"[\-~]", slot), str_slots):
                start = to_datetime(date, str_start or "00:00")
                end = to_datetime(date, str_end or "23:30")
                if end <= start:
                    raise AnswerFormException({date: f"`{str_start}-{str_end}` の入力が正しくありません。"})
                yield (start, end)


class AnswerFormException(Exception):
    pass
