FROM python:3.11-slim

# Dépendances système
RUN apt-get update && apt-get install -y \
    git curl ssh sudo

# Dépendances Python
COPY requirements.txt /opt/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /opt/requirements.txt \
    && apt-get clean

# Entrypoint
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Exposer le port utilisé par l'app
EXPOSE 8000

# Lancer l'app Flask ou autre
WORKDIR /app
CMD ["/entrypoint.sh"]
