FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg DATA_DIR=/app/data
WORKDIR /app
RUN groupadd --gid 10001 bot && useradd --uid 10001 --gid bot --create-home bot
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=bot:bot *.py ./
RUN mkdir -p /app/data && chown bot:bot /app/data
USER bot
CMD ["python", "main.py"]
