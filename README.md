# Aircover Skills

Installable [Claude Skills](https://www.anthropic.com/news/skills) built on the
Aircover MCP. Each skill turns live Aircover deal, meeting, and agent data into a
finished work product. Skills are self-contained: everything org-specific lives in
each skill's `config.json`, so the same skill works for any company whose team uses
Aircover.

## Skills in this repo

| Skill | What it does |
|---|---|
| [`aircover-mutual-action-plan`](aircover-mutual-action-plan/) | Generates a completed Mutual Action Plan (MAP) spreadsheet for a deal: the shared, dated roadmap from discovery to go-live, filled from the account, opportunity, sponsors, target go-live date, and current deal progress. |

## Install a skill

**One-click:** download the skill's `.skill` file from this repo's
[Releases](../../releases) and add it under Customize > Skills (personal) or
Organization settings > Skills (org-wide, on Team or Enterprise). Each user logs
into the Aircover connector once.

**Build from source:** each skill ships a standard-library packager (no
dependencies). From inside the skill's folder:
```
cd aircover-mutual-action-plan
python package.py dist
```
This writes `dist/<skill-name>.skill`, ready to upload under Customize > Skills.

## Requirements

- The Aircover connector connected (Production by default; see each skill's
  `config.json` to change environment).
- Code execution / file creation enabled in the client.
- Any Python dependencies a skill names in its README (for example openpyxl).

## Repo layout

```
.
  README.md                      this index
  LICENSE                        repo license (MIT)
  aircover-mutual-action-plan/   one self-contained skill (SKILL.md at its root)
    SKILL.md  config.json  README.md  LICENSE  package.py
    scripts/  assets/  references/
```

Each skill folder is independently buildable and installable. To add a new skill,
drop a new self-contained folder alongside the existing ones and add a row to the
table above.

## License

MIT (see [`LICENSE`](LICENSE)). Each skill folder also carries its own license.

## Privacy

Skills read deal, meeting, and agent data from the connected Aircover account at
run time. Nothing is stored or sent anywhere else. Run against your own org's data
only.
