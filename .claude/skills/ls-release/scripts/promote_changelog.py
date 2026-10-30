#!/usr/bin/env python3
"""Promote the [Unreleased] block of CHANGELOG.md into a dated release section.

Usage:
  python3 promote_changelog.py --version 1.2.3 --date 2026-11-30 \
      --intro FILE --contributors FILE [--changelog CHANGELOG.md] [--write]
  python3 promote_changelog.py --self-test

Inserts an empty `## [Unreleased]`, then `## [X.Y.Z] — DATE`, the intro paragraph,
the existing bullets, and a `### Contributors` block before the next release
heading. Prints the new section to stdout unless --write. Existing bullets are
left untouched, so their wording is finalised before the promotion.
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

HEADING = "## [Unreleased]\n"


def promote(text: str, version: str, date: str, intro: str, contributors: str) -> str:
    if not text.startswith(HEADING):
        raise SystemExit("CHANGELOG does not start with '## [Unreleased]'")
    if re.search(r"^## \[%s\]" % re.escape(version), text, re.M):
        raise SystemExit(f"CHANGELOG already has a [{version}] heading")
    if re.search(r"^## \[Unreleased\]", text[len(HEADING):], re.M):
        raise SystemExit("more than one [Unreleased] heading")

    body = text[len(HEADING):]
    contributors = contributors.strip()
    if not contributors.startswith("### Contributors"):
        contributors = "### Contributors\n\n" + contributors

    # Contributors go after the last bullet and before the next release heading.
    nxt = re.search(r"^## \[", body, re.M)
    end = nxt.start() if nxt else len(body)
    parts = [f"## [{version}] — {date}", intro.strip(), body[:end].strip("\n"), contributors]
    section = "\n\n".join(p for p in parts if p)

    return HEADING + "\n" + section + "\n\n" + body[end:]


def self_test() -> int:
    src = "## [Unreleased]\n\n### Added\n\n- A thing.\n\n## [0.1.0] — 2026-01-01\n\nOld.\n"
    out = promote(src, "0.2.0", "2026-02-02", "Intro.", "- [@a](https://github.com/a): everything")
    assert out.startswith("## [Unreleased]\n\n## [0.2.0] — 2026-02-02\n\nIntro.\n"), out
    assert "Intro.\n\n### Added\n\n- A thing.\n" in out, out
    assert "### Contributors\n\n- [@a]" in out, out
    assert "## [0.1.0] — 2026-01-01\n\nOld.\n" in out, out
    # The anchor a release body links to: dots and the em dash go, spaces become dashes.
    head = re.search(r"^## \[(\S+)\] — (\S+)$", out, re.M)
    anchor = "#%s--%s" % (head.group(1).replace(".", "").lower(), head.group(2))
    assert anchor == "#020--2026-02-02", anchor
    for bad, why in (
        ("## Nope\n", "no Unreleased heading"),
        ("## [Unreleased]\n\n## [0.2.0] — x\n", "version already present"),
        ("## [Unreleased]\n\n## [Unreleased]\n", "two Unreleased headings"),
    ):
        try:
            promote(bad, "0.2.0", "2026-02-02", "i", "c")
        except SystemExit:
            pass
        else:
            raise AssertionError(f"expected a refusal: {why}")
    with tempfile.TemporaryDirectory() as td:
        path = Path(td, "CHANGELOG.md")
        path.write_text(src)
        path.write_text(promote(path.read_text(), "0.2.0", "2026-02-02", "Intro.", "- @a: everything"))
        assert "## [0.2.0]" in path.read_text()
    print("self-test ok")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--changelog", default="CHANGELOG.md")
    ap.add_argument("--version")
    ap.add_argument("--date")
    ap.add_argument("--intro", help="file with the intro paragraph")
    ap.add_argument("--contributors", help="file with the Contributors block")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--self-test", action="store_true", dest="self_test")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    missing = [n for n in ("version", "date", "intro", "contributors") if not getattr(a, n)]
    if missing:
        ap.error("missing required argument(s): " + ", ".join("--" + m for m in missing))

    new = promote(
        Path(a.changelog).read_text(),
        a.version,
        a.date,
        Path(a.intro).read_text(),
        Path(a.contributors).read_text(),
    )
    if a.write:
        Path(a.changelog).write_text(new)
        print(f"promoted {a.changelog} to [{a.version}] — {a.date}")
    else:
        # Print the new section only: from its heading to the next release heading.
        start = new.index(f"## [{a.version}]")
        nxt = re.search(r"^## \[", new[start + 3:], re.M)
        print(new[start : start + 3 + nxt.start()] if nxt else new[start:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
