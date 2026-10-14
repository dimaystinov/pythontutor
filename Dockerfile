FROM python:3.14.7-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock \
    && groupadd --gid 10001 tutor \
    && useradd --uid 10001 --gid tutor --no-create-home tutor
COPY . .
RUN mkdir -p /app/data /app/collected_static \
    && SECRET_KEY=build-only-not-a-runtime-secret-000000000000000000000000 DATABASE_PATH=/tmp/build.sqlite3 \
       python manage.py collectstatic --noinput \
    && chown -R tutor:tutor /app/data /app/collected_static
USER tutor
EXPOSE 8000
ENTRYPOINT ["python", "scripts/entrypoint.py"]
CMD ["gunicorn", "pythontutor.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "180", "--access-logfile", "-", "--error-logfile", "-", "--no-control-socket"]
