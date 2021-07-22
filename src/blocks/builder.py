from blocks.base import Action, Button, Header, Section


def from_host(host, date, time, setting):
    return [
        Header("時間調整のご協力"),
        Section(mrkdwn="以下の内容で時間調整を行います。"),
        Section(mrkdwn=f"*主催者:*\n{host}", block_id="host"),
        Section(mrkdwn=f"*開催日:*\n{date}", block_id="date"),
        Section(mrkdwn=f"*開催時間:*\n{time}", block_id="time"),
        Section(mrkdwn=f"*回答設定:*\n{setting}", block_id="setting"),
        Action(
            Button(action_id="answer_schedule", value="answer_schedule",
                   text="回答する", style="primary"),
            Button(action_id="not_answer", value="answer_schedule",
                   text="不参加", style="danger"),
        )
    ]
