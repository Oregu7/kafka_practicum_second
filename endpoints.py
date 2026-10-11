from pathlib import Path

import yaml
from aiohttp_swagger import setup_swagger
from faust.web import View

from app import BlockCommand, app, blocked_users_table, commands_topic, stop_words_table
from utils import normalize_word

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
@app.table_route(table=blocked_users_table, match_info="user_id")
async def get_blocked_users(web, request, user_id):
    return web.json({"blocked": blocked_users_table[user_id]})


@app.page("/blocked-users/{user_id}/{target_id}/")
class BlockUser(View):
    """POST - user_id блокирует target_id; команда уходит в топик и применяется агентом."""

    async def post(self, request, user_id, target_id):
        command = BlockCommand(user_id=user_id, target_id=target_id)
        await commands_topic.send(key=user_id, value=command)
        return self.json({"user_id": user_id, "target_id": target_id}, status=202)


@app.page("/stop-words/")
async def get_stop_words(web, request):
    return web.json(sorted(stop_words_table.keys()))


@app.page("/stop-words/{word}/")
class StopWord(View):
    async def post(self, request, word):
        stop_words_table[normalize_word(word)] = True
        return self.json(sorted(stop_words_table.keys()))

    async def delete(self, request, word):
        stop_words_table.pop(normalize_word(word), None)
        return self.json(sorted(stop_words_table.keys()))
