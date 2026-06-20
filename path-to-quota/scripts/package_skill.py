#!/usr/bin/env python3
"""
package_skill.py  -  Validate a skill folder and zip it into an installable .skill file.

Usage:
    python package_skill.py <path/to/skill-folder> [output-dir]

Validates the frontmatter rules that claude.ai / the Skills API enforce on upload,
then packages the folder. Self-contained (standard library only).
"""
import re, sys, zipfile
from pathlib import Path

EXCLUDE_DIRS = {"__pycache__", "node_modules", ".git"}
EXCLUDE_GLOBS = ("*.pyc",)
EXCLUDE_FILES = {".DS_Store"}

def validate(skill_path: Path):
    md = skill_path / "SKILL.md"
    if not md.exists():
        return False, "SKILL.md not found at skill root"
    # exactly one SKILL.md
    extras = [p for p in skill_path.rglob("SKILL.md") if p.resolve() != md.resolve()]
    if extras:
        return False, "More than one SKILL.md. Rename reference files (e.g. references/topic.md). Extra: " + \
               ", ".join(str(p.relative_to(skill_path)) for p in extras)
    content = md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return False, "No YAML frontmatter found"
    fm = m.group(1)
    def field(key):
        fm_m = re.search(r"^" + key + r":\s*(.+?)\s*$", fm, re.MULTILINE)
        return fm_m.group(1).strip() if fm_m else None
    name = field("name")
    desc = field("description")
    if not name:
        return False, "Missing 'name' in frontmatter"
    if not desc:
        return False, "Missing 'description' in frontmatter"
    if not re.match(r"^[a-z0-9-]+$", name):
        return False, f"Name '{name}' must be kebab-case (lowercase letters, digits, hyphens)"
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return False, f"Name '{name}' cannot start/end with a hyphen or contain '--'"
    if len(name) > 64:
        return False, f"Name too long ({len(name)} chars, max 64)"
    if "<" in desc or ">" in desc:
        return False, "Description cannot contain angle brackets (< or >)"
    if len(desc) > 1024:
        return False, f"Description too long ({len(desc)} chars, max 1024)"
    return True, "valid"

def excluded(rel: Path):
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return True
    if rel.name in EXCLUDE_FILES:
        return True
    return any(rel.match(g) for g in EXCLUDE_GLOBS)

def package(folder, out_dir=None):
    skill_path = Path(folder).resolve()
    if not skill_path.is_dir():
        print("Error: not a folder:", skill_path); return None
    ok, msg = validate(skill_path)
    if not ok:
        print("VALIDATION FAILED:", msg); return None
    out_dir = Path(out_dir).resolve() if out_dir else Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (skill_path.name + ".skill")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(skill_path.rglob("*")):
            if f.is_file():
                rel = f.relative_to(skill_path.parent)
                if not excluded(f.relative_to(skill_path)):
                    z.write(f, rel.as_posix())
    print("Validated and packaged:", out)
    return out

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python package_skill.py <skill-folder> [output-dir]"); sys.exit(1)
    res = package(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    sys.exit(0 if res else 1)
