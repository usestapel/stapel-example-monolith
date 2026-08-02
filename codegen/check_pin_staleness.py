#!/usr/bin/env python3
"""Fleet-release staleness gate for svc-app/requirements.txt.

The existing `make codegen-check` gate (.github/workflows/codegen.yml) only
proves the committed codegen artifacts are self-consistent with whatever
`pip install -r requirements.txt` resolves to *right now*. That is meaningless
against staleness: if the pins are old, pip installs old libraries, codegen
regenerates from those old libraries, and the diff against the (also old)
committed aggregate is zero. Green, and wrong — this is exactly how the
aggregate silently rotted for months (see git history around 93c010c /
7c913d8): every input was self-consistent, none of it was current.

The only source of truth for "current" is PyPI itself — this is inherently a
cross-repo check (each stapel-* library ships on its own cadence from its own
repo) that cannot be answered by anything committed in this repo. It does
*not*, however, need to run in each of those ten repos: PyPI is a single
shared oracle, so the check can live here, in the one repo whose pins are
being judged, as long as it asks PyPI rather than itself.

Policy: a pin is stale if PyPI's latest release for that package is not
covered by the pinned range at all (the range's ceiling is behind the latest
release's minor). This intentionally does NOT require pinning the exact
latest — a range one minor below latest is normal (release lag), the failure
mode this catches is "PyPI moved to a minor this range can never resolve to,"
which is the state that produces ResolutionImpossible once a sibling
package's floor moves past our ceiling.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

REQUIREMENTS = Path(__file__).resolve().parent.parent / "svc-app" / "requirements.txt"

# Matches lines like: stapel-auth>=0.19,<0.20
PIN_RE = re.compile(
    r"^(stapel-[a-z0-9-]+)>=(\d+)\.(\d+)(?:\.(\d+))?,<(\d+)\.(\d+)\s*$"
)


def parse_pins(text: str) -> dict[str, tuple[tuple[int, ...], tuple[int, int]]]:
    pins = {}
    for line in text.splitlines():
        line = line.strip()
        m = PIN_RE.match(line)
        if not m:
            continue
        name = m.group(1)
        floor = tuple(int(g) for g in m.groups()[1:4] if g is not None)
        ceiling = (int(m.group(5)), int(m.group(6)))
        pins[name] = (floor, ceiling)
    return pins


def latest_version(package: str, attempts: int = 3) -> tuple[int, int, int]:
    url = f"https://pypi.org/pypi/{package}/json"
    last_exc: Exception | None = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.load(resp)
            break
        except Exception as exc:  # transient network/SSL hiccups happen
            last_exc = exc
    else:
        raise last_exc  # type: ignore[misc]
    version = data["info"]["version"]
    parts = version.split(".")[:3]
    while len(parts) < 3:
        parts.append("0")
    return tuple(int(re.match(r"\d+", p).group()) for p in parts)


def main() -> int:
    pins = parse_pins(REQUIREMENTS.read_text())
    if not pins:
        print("No stapel-* range pins found — nothing to check.", file=sys.stderr)
        return 1

    stale: list[str] = []
    for name, (_floor, ceiling) in sorted(pins.items()):
        try:
            latest = latest_version(name)
        except Exception as exc:  # network hiccup shouldn't be silent
            print(f"WARN: could not fetch {name} from PyPI: {exc}", file=sys.stderr)
            continue

        latest_minor = latest[:2]
        if latest_minor >= ceiling:
            stale.append(
                f"  {name}: pin ceiling <{ceiling[0]}.{ceiling[1]} — "
                f"PyPI latest is {'.'.join(str(p) for p in latest)} "
                f"(minor {latest_minor[0]}.{latest_minor[1]}, at or past the ceiling)"
            )
        else:
            print(
                f"OK    {name}: latest {'.'.join(str(p) for p in latest)}, "
                f"pin ceiling <{ceiling[0]}.{ceiling[1]}"
            )

    if stale:
        print(
            "\nSTALE: the following pins in svc-app/requirements.txt no longer "
            "cover PyPI's current release — bump the range:",
            file=sys.stderr,
        )
        for line in stale:
            print(line, file=sys.stderr)
        return 1

    print("\nAll stapel-* pins cover PyPI's current releases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
