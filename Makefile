# Stapel example monolith — codegen source (docs/flow-system.md §0.1).
#
# The monolith doubles as the all-modules codegen instance: it emits the unified
# OpenAPI schema.json + flows.json that the frontend TS client is generated from.
PYTHON ?= /Users/apple/Projects/stapel/.venv/bin/python
GEN_DIR := codegen/generated

.PHONY: codegen codegen-check

# Regenerate the committed backend artifacts (schema.json + flows.json).
codegen:
	PYTHON=$(PYTHON) codegen/generate.sh $(abspath $(GEN_DIR))

# Drift gate: regenerate into a temp dir and diff against the committed
# artifacts. Non-zero exit (red CI) on any divergence — the whole point of the
# byte-stable encoding is that a no-op regen is a no-op diff.
codegen-check:
	@tmp=$$(mktemp -d); \
	PYTHON=$(PYTHON) codegen/generate.sh $$tmp >/dev/null; \
	if ! diff -ru $(GEN_DIR) $$tmp; then \
		echo "DRIFT: committed codegen artifacts are stale — run 'make codegen' and commit." >&2; \
		rm -rf $$tmp; exit 1; \
	fi; \
	rm -rf $$tmp; \
	echo "codegen artifacts up to date."
