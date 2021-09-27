import json
import re


def camel_to_snake(case):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', case).lower()


class Text(dict):
    def __init__(self, text, *args, **kwargs):
        super().__init__(type=self.text_type, text=text, *args, **kwargs)

    @property
    def text_type(self):
        return camel_to_snake(self.__class__.__name__)


class PlainText(Text):
    pass


class Mrkdwn(Text):
    pass


class Json(dict):
    def __str__(self) -> str:
        return json.dumps(self, indent=4)

    @property
    def type(self):
        return camel_to_snake(self.__class__.__name__)


class Modal(Json):
    def __init__(self, callback_id, title, submit, blocks=[], *args, **kwargs):
        super().__init__(type=self.type, callback_id=callback_id,
                         title=PlainText(title), submit=PlainText(submit),
                         blocks=blocks, *args, **kwargs)


class Block(Json):
    def __init__(self, block_id=None, accessory=None, *args, **kwargs):
        kwargs.setdefault("type", self.type)
        super().__init__(*args, **kwargs)
        if block_id:
            self["block_id"] = block_id
        if accessory:
            self["accessory"] = accessory


class Actions(Block):
    def __init__(self, *elements):
        super().__init__(elements=list(elements))


class Section(Block):
    def __init__(self, text, *args, **kwargs):
        super().__init__(text=Mrkdwn(text), *args, **kwargs)


class Header(Block):
    def __init__(self, text, *args, **kwargs):
        super().__init__(text=PlainText(text), *args, **kwargs)


class Button(Block):
    def __init__(self, action_id, value, text, style, *args, **kwargs):
        super().__init__(text=PlainText(text),
                         style=style, value=value, action_id=action_id,
                         *args, **kwargs)


class Picker(Block):
    def __init__(self, action_id, initial, *args, **kwargs):
        super().__init__(action_id=action_id, *args, **kwargs)
        self[self.initial_field] = str(initial)

    @property
    def initial_field(self):
        category = re.match(r"(.+)picker", self.__class__.__name__).group(1).lower()
        return f"initial_{category}"


class Datepicker(Picker):
    pass


class Timepicker(Picker):
    pass


class Input(Block):
    def __init__(self, action_id=None, label=" ", optional=False, *args, **kwargs):
        super().__init__(type="input",
                         optional=optional,
                         element=dict(type=self.element_type, action_id=action_id),
                         label=PlainText(label), *args, **kwargs)

    @property
    def element_type(self):
        return camel_to_snake(self.__class__.__name__)


class PlainTextInput(Input):
    def __init__(self, initial=None, placeholder=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if initial:
            self["element"]["initial_value"] = initial
        if placeholder:
            self["element"]["placeholder"] = PlainText(placeholder)


class ChannelsSelect(Input):
    pass


class MultiUsersSelect(Input):
    pass


class RadioButtons(Input):
    def __init__(self, options, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["element"]["options"] = [dict(text=PlainText(text), value=value)
                                      for text, value in options]


if __name__ == "__main__":
    tmp = RadioButtons(block_id="display_result", action_id="result-option",
                       options=[("主催者だけに回答を送る", "host"),
                                ("回答者に全員の回答を公開する", "all")])

    print(tmp)
