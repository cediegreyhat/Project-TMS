# Contributing

## Dev Setup

```bash
git clone https://github.com/cediegreyhat/Project-LMS.git
cd Project-LMS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
```

## Code Style
- Follow PEP 8; keep functions focused and small.
- Business rules go in `service.py`, never in presentation code.
- SQL goes in `database.py` and must be parameterised.
- Colors / theme constants live in `gui/theme.py` only.

## Tests
- Run `python -m pytest tests/ -q` before opening a PR.
- Add tests for new service/DB behavior; GUI is not under automated test.

## Pull Requests
- One logical change per PR.
- Update docs when behavior changes.
- Reference the issue number in the PR description.
