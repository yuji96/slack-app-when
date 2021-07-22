# FIXME: base.py で定義したオブジェクト指向に置換する
class AnswerModal:
    def __init__(self, date, time):
        self.date = date
        self.time = time

    @property
    def date_input_block(self):
        return {
            "block_id": self.date,
            "type": "input",
            "label": {
                "type": "plain_text",
                "text": f"{self.date} の {self.time}"
            },
            "element": {
                "type": "plain_text_input",
                "action_id": "plain_text_input-action",
                "placeholder": {
                    "type": "plain_text",
                    "text": "例：14:00-15:00,17:30~18:00"
                }
            }
        }
