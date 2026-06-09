#!/usr/bin/env python3
"""
package.py  -  Build the installable .skill from this repo (standard library only).

Run from the repo root:
    python package.py [output-dir]

It reads the skill name from SKILL.md frontmatter, validates the frontmatter rules
the Skills uploader enforces, and writes <output-dir>/<name>.skill with the skill
files nested under a top-level <name>/ folder (the structure the uploader expects).
Default output-dir is the current directory.
"""
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INCLUDE = ["SKILL.md", "config.json", "README.md", "scripts", "assets", "references"]
EXCLUDE_DIRS = {"__pycache__", ".git", "node_modules", "dist"}
EXCLUDE_FILES = {".DS_Store"}
EXCLUDE_SUFFIX = (".pyc",)


def validate(skill_md: Path):
    if not skill_md.exists():
        sys.exit("SKILL.md not found at repo root.")
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        sys.exit("No YAML frontmatter found in SKILL.md.")
    fm = m.group(1)

    def field(key):
        fm_m = re.search(r"^" + key + r":\s*(.+?)\s*$", fm, re.MULTILINE)
        return fm_m.group(1).strip() if fm_m else None

    name = field("name")
    desc = field("description")
    if not name:
        sys.exit("Missing 'name' in frontmatter.")
    if not desc:
        sys.exit("Missing 'description' in frontmatter.")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
        sys.exit(f"Invalid name {name!r}: must be kebab-case, max 64 chars, no leading/trailing/double hyphen.")
    if "<" in desc or ">" in desc:
        sys.exit("Description must not contain angle brackets.")
    if len(desc) > 1024:
        sys.exit("Description must be under 1024 chars.")
    return name


def iter_files():
    for item in INCLUDE:
        p = ROOT / item
        if not p.exists():
            continue
        if p.is_file():
            yield p
        else:
            for f in p.rglob("*"):
                if f.is_file() \
                        and not any(part in EXCLUDE_DIRS for part in f.parts) \
                        and f.name not in EXCLUDE_FILES \
                        and f.suffix not in EXCLUDE_SUFFIX:
                    yield f


def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)
    name = validate(ROOT / "SKILL.md")
    out = out_dir / f"{name}.skill"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in iter_files():
            arc = Path(name) / f.relative_to(ROOT)
            z.write(f, arc.as_posix())
    print(f"Built {out}")


if __name__ == "__main__":
    main()
