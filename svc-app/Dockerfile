FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client git && rm -rf /var/lib/apt/lists/*
COPY svc-app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY svc-app .
ENV DJANGO_SETTINGS_MODULE=core.settings.prod
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
