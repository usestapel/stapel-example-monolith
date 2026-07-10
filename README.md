# Stapel Example — Monolith

Every Stapel feature module wired into **one** Django service. Same modules,
same code as the microservices example — only the assembly differs: modules
are mounted on their natural URL prefixes inside a single process, and
cross-module communication uses the in-process bus backend instead of NATS.

```
.
├── docker-compose.base.yml     # postgres, redis, nginx
├── docker-compose.yml          # dev: source mounts + debugpy
├── service-configs/
│   ├── nginx/nginx.conf         # single `location /` → svc-app
│   └── postgres/ensure-databases.sh
├── codegen/                    # all-modules codegen source (see below)
│   ├── generate.sh
│   └── generated/              # committed backend artifacts (schema/flows/errors/features)
├── Makefile                    # `make codegen` / `make codegen-check`
├── svc-app/                    # THE service (§29 layout)
│   ├── config/                 # config/settings/{base,dev,local,prod,codegen}.py + urls.py
│   │   └── settings/codegen.py  # hermetic sqlite instance for schema emission
│   ├── apps/app/               # the project's own app (regular apps/ package)
│   └── requirements.txt        # all stapel modules (pip, PyPI ranges)
└── svc-app.yml                 # app + celery + beat + healthcheck
```

URL layout (module paths match the microservices deployment, so a project
can split into services later without breaking clients):

- `/auth/api/…` — stapel_auth + stapel_gdpr
- `/profiles/api/…` — stapel_profiles
- `/notifications/api/…`, `/workspaces/api/…`, `/billing/api/…`, `/cdn/api/…`
- `/categories/api/…` — stapel_categories
- `/translate/api/…`, `/translate/dashboard/…` — stapel_translate
- `/admin/` — Django admin, `/health/` — health

## Run

```bash
cp .env.example .env   # or use the generated .env (already has secrets)
docker compose up -d
docker compose run --rm svc-app python manage.py migrate
```

## Codegen source (frontend pipeline)

This monolith doubles as the **all-modules codegen source** (docs/done/flow-system-v1.md
§0.1): the single live instance from which the frontend's typed client is
generated. Because emitting a schema is pure introspection, it runs on hermetic
in-memory sqlite (`config/settings/codegen.py`) — no postgres, no redis.

```bash
make codegen          # → codegen/generated/{schema,flows,errors}.json + features/
make codegen-check    # drift gate: regenerate + diff (red CI on divergence)
```

- `codegen/generated/schema.json` — unified OpenAPI for all modules
  (identical to the runtime `/schema/`).
- `codegen/generated/flows.json` — `generate_flow_docs` machine artifact.
- `codegen/generated/errors.json` — `generate_error_keys` registry.
- `codegen/generated/features/` — localized Gherkin bundles (en, ru); a
  byte-stable, deterministic emission, committed as an artifact.

The encoding is byte-stable, so a no-op regen is a no-op diff (that is what
`make codegen-check` and `.github/workflows/codegen.yml` enforce). Each
per-module slice is **byte-identical** to the triad that module emits on its
own — e.g. the `/workspaces/api/` slice equals `stapel-workspaces/docs/
schema.json` (asserted by that repo's `test_matches_monolith_workspaces_slice`).

Downstream: `stapel-react`'s `pnpm gen:api` reads this `schema.json` and runs
`openapi-typescript` → the typed `@stapel/core` API surface. `geo` is excluded
(needs spatialite) and is not in this monolith's module set.

## Tests

```bash
cd svc-app && python -m pytest          # runs against the compose postgres
python manage.py check                  # boots the full all-modules INSTALLED_APPS
```

## Monolith vs microservices

| | Monolith (this) | Microservices |
|---|---|---|
| Modules | all in one INSTALLED_APPS | one set per service |
| Module→module calls | in-process bus backend | NATS bus |
| Databases | one (`stapel_app`) | one per service |
| Scaling | whole app | per service |

The module code is identical — the bus abstraction (`stapel_core.bus`)
selects the transport via `STAPEL_BUS_BACKEND`.
