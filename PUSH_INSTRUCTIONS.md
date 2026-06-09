# How to push this to GitHub

This folder is a complete, ready-to-push repo (`aircover-skills`), a monorepo where
each skill is a self-contained folder. The current contents:

- `README.md` - index of all skills + install instructions
- `LICENSE`, `.gitignore` - repo level
- `aircover-mutual-action-plan/` - the first skill (SKILL.md at its root, plus
  config.json, README.md, LICENSE, package.py, scripts/, assets/, references/)

## Create the repo and push (HTTPS)

```bash
cd aircover-skills
git init -b main
git add .
git commit -m "Add aircover-skills monorepo with aircover-mutual-action-plan skill"

# Create the empty repo on github.com first (public, no README/license/.gitignore),
# then:
git remote add origin https://github.com/davidhlevy/aircover-skills.git
git push -u origin main
```

If you have the GitHub CLI, the create + push is one step from inside the folder:

```bash
cd aircover-skills
git init -b main && git add . && git commit -m "Initial commit"
gh repo create aircover-skills --public --source=. --remote=origin --push
```

## Build the installable .skill (optional)

The repo ships a standard-library packager. From inside the skill folder:

```bash
cd aircover-mutual-action-plan
python package.py dist      # writes dist/aircover-mutual-action-plan.skill
```

A prebuilt `aircover-mutual-action-plan.skill` was sent alongside this zip, ready to
attach to a GitHub Release so customers can one-click install it.

## Adding more skills later

Drop a new self-contained skill folder next to `aircover-mutual-action-plan/` (its own
SKILL.md, config.json, package.py, etc.) and add a row to the table in the root README.
