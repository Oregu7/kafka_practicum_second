from pathlib import Path

import yaml
from aiohttp_swagger import setup_swagger
from faust.web import View

from worker.app import app, blocked_users_table, blocked_users_topic, messages_topic, stop_words_table, stop_words_topic
from worker.models import BlockCommand, Message, StopWordCommand
from worker.utils import normalize_word

# ---------------------------------------------------------------------------
# Swagger
# ---------------------------------------------------------------------------

OPENAPI = yaml.safe_load(Path(__file__).with_name("openapi.yaml").read_text(encoding="utf-8"))


def setup_docs(web):
    """Swagger UI на /docs, спецификация на /docs/swagger.json; вызывается при старте веб-сервера Faust."""
    setup_swagger(web.web_app, swagger_info=OPENAPI, swagger_url="/docs", ui_version=3)


app.on_webserver_init = setup_docs


# ---------------------------------------------------------------------------
# HTTP-эндпоинты
# ---------------------------------------------------------------------------

@app.page("/blocked-users/{user_id}/")
class BlockedUsers(View):
    @app.table_route(table=blocked_users_table, match_info="user_id")
    async def get(self, request, user_id):
        return self.json({"blocked": blocked_users_table[user_id]})

    async def post(self, request, user_id):
        try:
            target_id = (await request.json())["target_id"]
        except (ValueError, KeyError, TypeError):
            target_id = None
        if not isinstance(target_id, str) or not target_id:
            return self.json({"error": "ожидается JSON {target_id}, значение - непустая строка"}, status=400)
        command = BlockCommand(user_id=user_id, target_id=target_id)
        await blocked_users_topic.send(key=user_id, value=command)
        return self.json({"user_id": user_id, "target_id": target_id}, status=202)


@app.page("/messages/")
class SendMessage(View):
    async def post(self, request):
        try:
            payload = await request.json()
            fields = [payload[name] for name in ("sender_id", "recipient_id", "text")]
        except (ValueError, KeyError, TypeError):
            fields = None
        if not fields or not all(isinstance(f, str) and f for f in fields):
            return self.json({"error": "ожидается JSON {sender_id, recipient_id, text}, все поля - непустые строки"},
                             status=400)
        msg = Message(*fields)
        await messages_topic.send(key=msg.recipient_id, value=msg)
        return self.json({"sender_id": msg.sender_id, "recipient_id": msg.recipient_id, "text": msg.text}, status=202)


@app.page("/stop-words/")
async def get_stop_words(web, request):
    return web.json(sorted(stop_words_table.keys()))


@app.page("/stop-words/{word}/")
class StopWord(View):
    async def post(self, request, word):
        return await self._send(word, "add")

    async def delete(self, request, word):
        return await self._send(word, "remove")

    async def _send(self, word, action):
        word = normalize_word(word)
        await stop_words_topic.send(key=word, value=StopWordCommand(word=word, action=action))
        return self.json({"word": word, "action": action}, status=202)
