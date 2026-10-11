"""Заполняет стоп-слова и блокировки тестовыми данными через HTTP воркера.

    python seeds/load.py [URL]        # по умолчанию http://127.0.0.1:6066
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SEEDS = Path(__file__).parent
URL = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:6066").rstrip("/")


def post(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(URL + path, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10).read()


def load(name):
    return json.loads((SEEDS / name).read_text(encoding="utf-8"))


quote = urllib.parse.quote

stop_words = load("stop_words.json")
for word in stop_words:
    post(f"/stop-words/{quote(word)}/")
print(f"стоп-слов: {len(stop_words)}")

blocks = [(user, target) for user, targets in load("blocked_users.json").items() for target in targets]
for user_id, target_id in blocks:
    post(f"/blocked-users/{quote(user_id)}/", {"target_id": target_id})
print(f"блокировок: {len(blocks)} (применяются агентом асинхронно)")
