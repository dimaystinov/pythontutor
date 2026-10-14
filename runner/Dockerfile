FROM python:3.14.7-slim
RUN apt-get update && apt-get install -y --no-install-recommends docker-cli && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --only-binary=:all: Pillow==12.3.0
WORKDIR /app
COPY runner /app/runner
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8081
CMD ["python", "-m", "runner.server"]
