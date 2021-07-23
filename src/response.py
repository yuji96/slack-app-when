from typing import Iterable


class Data(dict):  # TODO: 名前の再考
    def __init__(self, body: dict, view: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.body = body
        self.view = view
        self.values_ = view["state"]["values"]
        self.set_modal_inputs()

    @property
    def members(self) -> Iterable:
        target = self.body["view"]["callback_id"]
        if target == 'set_schedules-im':
            return self.values_["users_select"]["multi_users_select-action"]["selected_users"]
        else:
            yield list(self.values_["channel_select"].values())[0]["selected_channel"]

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
