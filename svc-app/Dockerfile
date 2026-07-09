FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*
COPY svc-app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# stapel_core is vendored as a git submodule at the project root
COPY stapel_core ./stapel_core
COPY svc-app .
ENV DJANGO_SETTINGS_MODULE=config.settings.prod
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
