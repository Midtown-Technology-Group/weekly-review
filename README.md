# Weekly Review Generator

Automate your GTD weekly review. Save 30 minutes every Friday.

## Installation

```bash
pip install weekly-review
```

## Usage

```bash
# Generate review for current week
weekly-review generate

# Generate for specific week
weekly-review generate 2026-W16

# Include last week
weekly-review --last-week

# Dry run (preview only)
weekly-review generate --dry-run
```

## Output

Creates `reviews/weekly/YYYY-W##.md` with:

- Week at a Glance (metrics)
- Completed This Week
- Key Decisions & Notes
- People This Week
- Meetings & Time Blocks
- Active Projects
- Carry-Over Suggestions (prioritized)
- Waiting-For Aging Check

## License

AGPL-3.0
