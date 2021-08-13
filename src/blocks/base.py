import json


class Text(dict):
    TEXT_TYPE = None

    def __init__(self, text, *args, **kwargs):
        super().__init__(type=self.TEXT_TYPE, text=text, *args, **kwargs)


class PlainText(Text):
    TEXT_TYPE = "plain_text"


class MarkDown(Text):
    TEXT_TYPE = "mrkdwn"


class Json(dict):
    def __str__(self) -> str:
        return json.dumps(self, indent=4)


class Modal(Json):
    def __init__(self, callback_id, title, submit, blocks=[], *args, **kwargs):
        super().__init__(type="modal", callback_id=callback_id,
                         title=PlainText(title), submit=PlainText(submit),
                         blocks=blocks, *args, **kwargs)


class Block(Json):
    TYPE = None

    def __init__(self, block_id=None, accessory=None, *args, **kwargs):
        super().__init__(type=self.TYPE, *args, **kwargs)
        if block_id:
            self["block_id"] = block_id
        if accessory:
            self["accessory"] = accessory


class Action(Block):
    TYPE = "actions"

    def __init__(self, *elements):
        super().__init__(elements=list(elements))


class Section(Block):
    TYPE = "section"

    def __init__(self, text, *args, **kwargs):
        super().__init__(text=MarkDown(text), *args, **kwargs)


class Header(Block):
    TYPE = "header"

    def __init__(self, text, *args, **kwargs):
        super().__init__(text=PlainText(text), *args, **kwargs)


class Button(Block):
    TYPE = "button"

    def __init__(self, action_id, value, text, style, *args, **kwargs):
        super().__init__(text=PlainText(text),
                         style=style, value=value, action_id=action_id,
                         *args, **kwargs)


class Picker(Block):
    def __init__(self, action_id, initial, *args, **kwargs):
        super().__init__(action_id=action_id, *args, **kwargs)
        self[self.initial_field] = str(initial)


class DatePicker(Picker):
    TYPE = "datepicker"
    initial_field = "initial_date"


class TimePicker(Picker):
    TYPE = "timepicker"
    initial_field = "initial_time"


class Input(Block):
    TYPE = "input"
    ELEMENT_TYPE = None

    def __init__(self, action_id=None, label=" ", optional=False, *args, **kwargs):
        super().__init__(optional=optional,
                         element=dict(type=self.ELEMENT_TYPE, action_id=action_id),
                         label=PlainText(label), *args, **kwargs)


class PlainTextInput(Input):
    ELEMENT_TYPE = "plain_text_input"

    def __init__(self, initial=None, placeholder=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if initial:
            self["element"]["initial_value"] = initial
        if placeholder:
            self["element"]["placeholder"] = PlainText(placeholder)


class ChannelsSelect(Input):
    ELEMENT_TYPE = "channels_select"


class UsersSelect(Input):
    ELEMENT_TYPE = "multi_users_select"


class RadioButtons(Input):
    ELEMENT_TYPE = "radio_buttons"

    def __init__(self, options, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["element"]["options"] = [dict(text=PlainText(text), value=value)
                                      for text, value in options]


if __name__ == "__main__":
    tmp = RadioButtons(block_id="display_result", action_id="result-option",
                       options=[("主催者だけに回答を送る", "host"),
                                ("回答者に全員の回答を公開する", "all")])

    print(tmp)
