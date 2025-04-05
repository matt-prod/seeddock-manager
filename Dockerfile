FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    git curl ssh sudo \
    && pip install --upgrade pip \
    && pip install -r /opt/requirements.txt \
    && apt-get clean

COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app
CMD ["/entrypoint.sh"]
