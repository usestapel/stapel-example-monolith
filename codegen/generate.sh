#!/usr/bin/env bash
# Codegen source runner (docs/flow-system.md §0.1).
#
# Boots the all-modules monolith on hermetic sqlite and emits the backend
# artifacts the frontend codegen consumes:
#   codegen/generated/schema.json  — unified drf-spectacular OpenAPI (all modules)
#   codegen/generated/flows.json   — generate_flow_docs machine artifact
#   codegen/generated/errors.json  — generate_error_keys machine artifact
#   codegen/generated/features/    — localized Gherkin bundles
#
# Usage:
#   codegen/generate.sh [OUT_DIR]     # default: codegen/generated
#   PYTHON=/path/to/python codegen/generate.sh
#
# Drift gate: `make codegen-check` regenerates into a temp dir and diffs against
# the committed artifacts — any divergence fails (red CI).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
SVC="$ROOT/svc-app"

OUT_DIR="${1:-$ROOT/codegen/generated}"
PYTHON="${PYTHON:-/Users/apple/Projects/stapel/.venv/bin/python}"

export DJANGO_ENV="${DJANGO_ENV:-local}"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.codegen}"

cd "$SVC"
PYTHONPATH="$SVC${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" -m stapel_tools.codegen --out "$OUT_DIR"
