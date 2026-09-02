# Testing Rules for Explorers3web

## Add tests before final git check-in

For any implementation plan that introduces new game mechanics or system behaviour,
unit tests covering the new functionality must be added to `gametests.py` **before**
the final `git commit` that closes the plan.

- Tests live in `/Users/madbot/Explorers3web/gametests.py`
- Run with: `.venv/bin/python -m unittest gametests.TestClassName -v`
- Use `make_human()` / `make_robot()` helpers for controlled character state
- Each plan phase may accumulate tests; the final phase commit must include them all
