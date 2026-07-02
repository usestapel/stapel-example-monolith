# Stapel Example — Monolith

Every Stapel feature module wired into **one** Django service. Same modules,
same code as the microservices example — only the assembly differs: modules
are mounted on their natural URL prefixes inside a single process, and
cross-module communication uses the in-process bus backend instead of Kafka.

```
.
├── docker-compose.base.yml     # postgres, redis, nginx
├── docker-compose.yml          # dev: source mounts + debugpy
├── service-configs/
│   ├── nginx/nginx.conf        # single `location /` → svc-app
│   └── postgres/ensure-databases.sh
├── stapel_core/                # shared framework (git submodule)
├── svc-app/                    # THE service
│   ├── stapel_auth/            # feature modules (git submodules inside the service)
│   ├── stapel_gdpr/
│   ├── stapel_profiles/
│   ├── stapel_notifications/
│   ├── stapel_workspaces/
│   ├── stapel_billing/
│   ├── stapel_cdn/
│   ├── stapel_translate/
│   ├── core/settings/…         # INSTALLED_APPS = COMMON + all modules
│   └── core/urls.py            # each module on its natural prefix
└── svc-app.yml                 # app + celery + beat + healthcheck
```

URL layout (module paths match the microservices deployment, so a project
can split into services later without breaking clients):

- `/auth/api/…` — stapel_auth + stapel_gdpr
- `/profiles/api/…` — stapel_profiles
- `/notifications/api/…`, `/workspaces/api/…`, `/billing/api/…`, `/cdn/api/…`
- `/translate/api/…`, `/translate/dashboard/…` — stapel_translate
- `/admin/` — Django admin, `/api/health/` — health

## Run

```bash
cp .env.example .env   # fill in secrets
docker compose up -d
docker compose run --rm svc-app python manage.py migrate
```

## Monolith vs microservices

| | Monolith (this) | Microservices |
|---|---|---|
| Modules | all in one INSTALLED_APPS | one set per service |
| Module→module calls | in-process bus backend | Kafka bus |
| Databases | one (`stapel_app`) | one per service |
| Scaling | whole app | per service |

The module code is identical — the bus abstraction (`stapel_core.bus`)
selects the transport via `STAPEL_BUS_BACKEND`.
