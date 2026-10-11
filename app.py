import os

import faust

from utils import censor

BROKER = os.getenv(
    "KAFKA_BROKER",
    "kafka://127.0.0.1:9092;kafka://127.0.0.1:9095;kafka://127.0.0.1:9096",
)
PARTITIONS = 3


class Message(faust.Record, serializer="json"):
    sender_id: str
    recipient_id: str
    text: str


class BlockCommand(faust.Record, serializer="json"):
    user_id: str
    target_id: str


app = faust.App(
    "message-filter-app",
    broker=BROKER,
    topic_partitions=PARTITIONS,
    topic_replication_factor=3,
    autodiscover=["endpoints"],
)

messages_topic = app.topic("messages", key_type=str, value_type=Message)
commands_topic = app.topic("blocked_users", key_type=str, value_type=BlockCommand)
filtered_topic = app.topic("filtered_messages", key_type=str, value_type=Message)

blocked_users_table = app.Table(
    "blocked_users",
    partitions=PARTITIONS,
    default=list,
)

stop_words_table = app.GlobalTable(
    "stop_words",
    partitions=PARTITIONS,
    default=bool,
    use_partitioner=True,
)

# ---------------------------------------------------------------------------
# Агенты
# ---------------------------------------------------------------------------

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
