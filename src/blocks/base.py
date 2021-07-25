import json


class Modal(dict):
    def __init__(self, callback_id, title, submit, *args, **kwargs):
        super().__init__(type="modal", callback_id=callback_id,
                         title=dict(type="plain_text", text=title),
                         submit=dict(type="plain_text", text=submit),
                         *args, **kwargs)


class Block(dict):
    TYPE = None

    def __init__(self, block_id=None, accessory=None, *args, **kwargs):
        super().__init__(type=self.TYPE, *args, **kwargs)
        if block_id:
            self["block_id"] = block_id
        if accessory:
            self["accessory"] = accessory

    def __str__(self) -> str:
        return json.dumps(self, indent=4)


class Input(Block):
    TYPE = "input"

    def __init__(self, block_id, label, element, optional=False, *args, **kwargs):
        super().__init__(block_id=block_id, element=element, optional=optional,
                         label=dict(type="plain_text", text=label),
                         *args, **kwargs)


class Action(Block):
    TYPE = "actions"

    def __init__(self, *elements):
        super().__init__(elements=list(elements))


class Text(Block):  # TODO: いらない説
    TYPE = None

    def __init__(self, t_type, text, *args, **kwargs):
        super().__init__(text=dict(type=t_type, text=text), *args, **kwargs)


class Section(Text):
    TYPE = "section"

    def __init__(self, mrkdwn=None, *args, **kwargs):
        if mrkdwn:
            super().__init__(t_type="mrkdwn", text=mrkdwn, *args, **kwargs)


class Header(Text):
    TYPE = "header"

    def __init__(self, text, *args, **kwargs):
        super().__init__(t_type="plain_text", text=text,
                         *args, **kwargs)


class Button(Text):
    TYPE = "button"

    def __init__(self, action_id, value, text, style, *args, **kwargs):
        super().__init__(t_type="plain_text", text=text,
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


class PlainTextInput(Block):
    TYPE = "plain_text_input"

    def __init__(self, action_id, initial=None, placeholder=None, *args, **kwargs):
        super().__init__(action_id=action_id, *args, **kwargs)
        if initial:
            self["initial_value"] = initial
        if placeholder:
            self["placeholder"] = dict(type="plain_text", text=placeholder)


if __name__ == "__main__":
    tmp = Input(block_id="block_id", label="label",
                element=PlainTextInput(action_id="action_id", initial="inital", placeholder="text"))
    print(tmp)
