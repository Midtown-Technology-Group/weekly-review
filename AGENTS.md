# Weekly Review agent guidance

This Python tool aggregates LogSeq daily notes and work-context pages into a GTD weekly-review Markdown file. `src/weekly_review/` separates parsing, extraction, deduplication, configuration, templates, CLI, and writing. `tests/test_weekly_review.py` and fixtures cover the behavior. Read [README.md](README.md) for the intended output; treat [TECHNICAL_PLAN.md](TECHNICAL_PLAN.md) as design context to verify against source.

## Development and checks

Use Python 3.10+ and install `python -m pip install -e ".[dev]"`. Run `python -m pytest` using the repository's configured `tests/` and `src` paths. Ruff/Black/mypy settings are declared, but their presence is not evidence that CI runs each tool. Inspect workflows before asserting a release gate.

Preserve ISO-week/date-range boundaries, fuzzy matching semantics, carryover aging, section configuration, and Jinja rendering. Use synthetic graph fixtures and verify both stdout preview and file-output seams when changing writer/CLI behavior. `weekly-review generate --dry-run` previews without writing the review; it may still read configured graph data. Select an explicit disposable graph/config for validation.

## Graph and release boundaries

Do not overwrite human notes, journals, review edits, or source work-context pages as a side effect of testing. Confirm output location and existing-file handling before a real generation. Never commit real meeting, customer, task, or personnel content. Generated carryovers are suggestions, not completed task actions.

`invoke.ps1` starts from the wrapper's parent and can install the package automatically. Without a supplied or discovered configuration, that parent is the default graph root; a supplied `-ConfigPath` or discovered configuration makes the configuration file's parent the graph root. Inspect the effective source and output paths before running it. Verify options in `cli.py` rather than copying README examples blindly. Tag-driven MSI publication and machine installation are separate operational actions; follow the exact workflow/build script and report source checks separately from deployed behavior.
