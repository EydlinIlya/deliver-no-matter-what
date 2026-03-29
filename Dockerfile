FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .[web]

ENV DATA_DIR=/tmp/data
EXPOSE 8000

CMD uvicorn am_israel_hai_badge.web.app:app --host 0.0.0.0 --port ${PORT:-8000}
