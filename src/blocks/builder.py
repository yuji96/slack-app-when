from blocks.base import Action, Button, Header, Section


def from_host(host_id, start_date, end_date, start_time, end_time,
              setting=None, *args, **kwargs):
    header = Header("時間調整のご協力")
    sections = [Section(mrkdwn="以下の内容で時間調整を行います。"),
                Section(mrkdwn=f"*主催者:*\n<@{host_id}>", block_id="host"),
                Section(mrkdwn=f"*開催日:*\n{start_date} から {end_date}", block_id="date"),
                Section(mrkdwn=f"*開催時間:*\n{start_time} から {end_time}", block_id="time")]
    action = Action(Button(action_id="answer_schedule", value="answer_schedule",
                           text="回答する", style="primary"),
                    Button(action_id="not_answer", value="answer_schedule",
                           text="不参加", style="danger"))
    if setting:
        sections.append(Section(mrkdwn=f"*回答設定:*\n{setting}", block_id="setting"))
    return [header, *sections, action]
