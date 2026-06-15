# Migrating `meeting-copilot` to its own repository

The Background Meeting Co-pilot used to live in the `meeting-copilot/`
subdirectory of this repo. It is a completely separate application from the
Django **monitoring-tool** (no shared code or dependencies), so it now lives in
its own repository.

These steps extract the `meeting-copilot/` directory **with its full commit
history** and push it to a new standalone repo. Run them locally — they only use
standard `git`.

## 1. Create the new (empty) repository

Create an empty repository on GitHub, e.g. **`santana-jay/meeting-copilot`**.
Do **not** initialize it with a README/license (we are importing history).

## 2. Extract the subdirectory history into a new branch

From a full (non-shallow) clone of this repository:

```bash
git clone https://github.com/santana-jay/monitoring-tool.git
cd monitoring-tool

# Make sure you have full history (skip if you did a normal clone):
git fetch --unshallow 2>/dev/null || true

# Produce a branch whose root is the meeting-copilot/ contents, history intact:
git subtree split --prefix=meeting-copilot -b split-meeting-copilot
```

`split-meeting-copilot` now contains the 6 meeting-copilot commits with
`pyproject.toml`, `src/`, `tests/`, `README.md`, `RUNNING.md`, etc. at the root.

> Alternative (also fine): `git filter-repo --subdirectory-filter meeting-copilot`
> in a fresh clone, if you have [`git-filter-repo`](https://github.com/newren/git-filter-repo) installed.

## 3. Push that history to the new repo

```bash
git push https://github.com/santana-jay/meeting-copilot.git \
    split-meeting-copilot:main
```

## 4. Verify the new repo stands alone

```bash
git clone https://github.com/santana-jay/meeting-copilot.git
cd meeting-copilot
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest          # expect: 52 passed
```

See that repo's `README.md` and `RUNNING.md` for full install/run instructions.

## 5. Remove it from this repo

Once the new repo is verified, merge the companion pull request in this
repository that deletes `meeting-copilot/` and updates the root `README.md` to
point at the new location. (The old commits remain in this repo's history, so
the split above can always be re-derived if needed.)
