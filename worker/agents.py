from worker.app import app, blocked_users_table, commands_topic, filtered_topic, messages_topic, stop_words_table
from worker.models import Message
from worker.utils import censor


def is_sender_not_blocked(msg: Message) -> bool:
    return msg.sender_id not in blocked_users_table[msg.recipient_id]


def censor_stop_words(msg: Message) -> Message:
    msg.text = censor(msg.text, stop_words_table.keys())
    return msg


@app.agent(commands_topic)
async def handle_block_commands(stream):
    async for cmd in stream:
        blocked = blocked_users_table[cmd.user_id]
        blocked_users_table[cmd.user_id] = sorted({*blocked, cmd.target_id})


@app.agent(messages_topic)
async def filter_messages(stream):
    stream = stream.filter(is_sender_not_blocked)
    stream.add_processor(censor_stop_words)
    async for msg in stream:
        await filtered_topic.send(key=msg.recipient_id, value=msg)
