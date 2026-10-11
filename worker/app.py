import faust

from config.settings import (
    BLOCKED_USERS_TOPIC,
    FILTERED_TOPIC,
    KAFKA_BROKER,
    MESSAGES_TOPIC,
    PARTITIONS,
    REPLICATION_FACTOR,
)
from worker.models import BlockCommand, Message

app = faust.App(
    "message-filter-app",
    broker=KAFKA_BROKER,
    topic_partitions=PARTITIONS,
    topic_replication_factor=REPLICATION_FACTOR,
    autodiscover=["worker.agents", "worker.endpoints"],
    store="rocksdb://",
)

messages_topic = app.topic(MESSAGES_TOPIC, key_type=str, value_type=Message)
commands_topic = app.topic(BLOCKED_USERS_TOPIC, key_type=str, value_type=BlockCommand)
filtered_topic = app.topic(FILTERED_TOPIC, key_type=str, value_type=Message)

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
