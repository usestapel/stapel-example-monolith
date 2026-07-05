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

## Codegen source (frontend pipeline)

This monolith doubles as the **all-modules codegen source** (docs/flow-system.md
§0.1): the single live instance from which the frontend's typed client is
generated. Because emitting a schema is pure introspection, it runs on hermetic
in-memory sqlite (`core/settings/codegen.py`) — no postgres, no redis.

```bash
make codegen          # → codegen/generated/{schema.json, flows.json}
make codegen-check    # drift gate: regenerate + diff (red CI on divergence)
```

- `codegen/generated/schema.json` — unified OpenAPI for all 8 modules
  (`spectacular` management command; identical to the runtime `/schema/`).
- `codegen/generated/flows.json` — `generate_flow_docs` machine artifact.

Downstream: `stapel-react`'s `pnpm gen:api` reads this `schema.json` and runs
`openapi-typescript` → the typed `@stapel/core` API surface. Both sides are
byte-stable, so a no-op regen is a no-op diff. `geo` is excluded (needs
spatialite) and is not in this monolith's module set.

## Monolith vs microservices

| | Monolith (this) | Microservices |
|---|---|---|
| Modules | all in one INSTALLED_APPS | one set per service |
| Module→module calls | in-process bus backend | Kafka bus |
| Databases | one (`stapel_app`) | one per service |
| Scaling | whole app | per service |

The module code is identical — the bus abstraction (`stapel_core.bus`)
selects the transport via `STAPEL_BUS_BACKEND`.
