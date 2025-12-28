FROM python:3.12-slim

WORKDIR /app

# Install deps first for layer caching
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# App code + assets (assets is inside app/)
COPY app/ /app/

# Repo scripts (run_update.sh lives here)
COPY scripts/ /app/scripts/

# Entrypoint (scheduler loop + launches Flask)
COPY docker/entrypoint.sh /entrypoint.sh

ENV PYTHONUNBUFFERED=1
EXPOSE 8181

RUN chmod +x /entrypoint.sh /app/scripts/run_update.sh

CMD ["/entrypoint.sh"]

