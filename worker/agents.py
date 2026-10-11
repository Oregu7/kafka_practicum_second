import logging

from worker.app import (
    app,
    blocked_users_table,
    blocked_users_topic,
    filtered_topic,
    messages_topic,
    stop_words_table,
    stop_words_topic,
)
from worker.models import Message
from worker.utils import censor

log = logging.getLogger(__name__)


def is_sender_not_blocked(msg: Message) -> bool:
    if msg.sender_id in blocked_users_table[msg.recipient_id]:
        log.info("сообщение от %s для %s отброшено: отправитель заблокирован", msg.sender_id, msg.recipient_id)
        return False
    return True


def censor_stop_words(msg: Message) -> Message:
    msg.text = censor(msg.text, stop_words_table.keys())
    return msg


@app.agent(blocked_users_topic)
async def handle_blocked_users(stream):
    async for cmd in stream:
        blocked = blocked_users_table[cmd.user_id]
        blocked_users_table[cmd.user_id] = sorted({*blocked, cmd.target_id})


@app.agent(stop_words_topic)
async def handle_stop_words(stream):
    # таблицы с RocksDB-хранилищем меняются только из агента: нужен текущий event, в HTTP-обработчике его нет
    async for cmd in stream:
        if cmd.action == "add":
            stop_words_table[cmd.word] = True
        else:
            stop_words_table.pop(cmd.word, None)


@app.agent(messages_topic)
async def filter_messages(stream):
    stream = stream.filter(is_sender_not_blocked)
    stream.add_processor(censor_stop_words)

    async for msg in stream:
        await filtered_topic.send(key=msg.recipient_id, value=msg)
