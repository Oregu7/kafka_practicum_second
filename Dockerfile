FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config ./config
COPY worker ./worker
COPY consumers ./consumers
COPY producers ./producers

EXPOSE 6066

CMD ["faust", "-A", "worker.app", "worker", "-l", "info"]
