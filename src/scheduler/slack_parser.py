class SchedulerCreationFormData(dict):
    def __init__(self, body: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.body = body
        self.values_ = body["view"]["state"]["values"]
        self.set_modal_inputs()

    @property
    def members(self) -> list[str]:
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
