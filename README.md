# Weekly Review Generator

Automate your GTD weekly review. Save 30 minutes every Friday.

## Features

- **Automatic Aggregation**: Pulls from `daily/*.md` and `pages/work-context___*.md`
- **Smart Deduplication**: Fuzzy matching prevents duplicate tasks/people/projects
- **GTD-Aligned Output**: Clean markdown with completed tasks, decisions, people, meetings
- **Prioritized Carry-Overs**: Suggests what to carry forward based on age and priority
- **ISO Week Support**: Generate for current week, specific week, or custom date ranges

## Installation

### From Source (Development)

```powershell
# Clone/navigate to the project
cd weekly-review

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install in editable mode
pip install -e .
```

### PowerShell Wrapper (Recommended)

The PowerShell wrapper handles venv activation automatically:

```powershell
# Generate review for current week
.\weekly-review\invoke.ps1

# Generate for specific week
.\weekly-review\invoke.ps1 -Week "2026-W16"

# Include previous week for comparison
.\weekly-review\invoke.ps1 -IncludeLastWeek

# Dry run (preview to stdout)
.\weekly-review\invoke.ps1 -DryRun

# Custom date range
.\weekly-review\invoke.ps1 -StartDate "2026-04-14" -EndDate "2026-04-20"

# Specify output file
.\weekly-review\invoke.ps1 -OutputPath "reviews/weekly/my-review.md"
```

## CLI Usage

```bash
# Generate review for current week
weekly-review generate

# Generate for specific ISO week
weekly-review generate 2026-W16

# Custom date range
weekly-review generate --start-date 2026-04-14 --end-date 2026-04-20

# Preview only (stdout, no file write)
weekly-review generate --dry-run

# Include last week for comparison
weekly-review generate --include-last-week

# Specify custom output path
weekly-review generate --output-path reviews/weekly/custom.md

# Show config and exit
weekly-review config
```

## Configuration

Create `weekly-review.yaml` in your knowledge graph root:

```yaml
# Paths (relative to knowledge graph root)
daily_notes_path: daily
work_context_path: pages
output_path: reviews/weekly

# Fuzzy matching threshold (0-100, default 85)
fuzzy_threshold: 85

# Date format for parsing
date_format: "%Y-%m-%d"

# Sections to include in output
sections:
  - metrics
  - completed
  - decisions
  - people
  - meetings
  - projects
  - carryovers
  - waiting_for

# Template settings
template: default  # or path to custom jinja2 template
```

## Output Format

Generated files: `reviews/weekly/YYYY-W##.md`

```markdown
# Weekly Review — 2026-W16 (Apr 14-20)

## Week at a Glance
| Metric | Count |
|--------|-------|
| Days with entries | 5/7 |
| Completed tasks | 23 |
| Unique people | 8 |
| Meetings | 6 |
| Decisions captured | 4 |

## Completed This Week
- [x] Migrated CIPP automatic deployments
- [x] Fixed Halo ticket import for INIM
...

## Key Decisions & Notes
- **CIPP**: Standard to disable Direct Send for MSP/Vitals+/Vitals/Block Hour
- **Idemeum**: Application control with approval flow implemented
...

## People This Week
- [[Mike]] - Brothers Excavating migration discussion
- [[Steven Keath]] - Direct Send chat
...

## Meetings & Time Blocks
- Call with Mike (9:37-10:00) - Brothers Excutating migration
- Holeman sync with Matt (14:00-14:20)
...

## Active Projects
- [[projects/bifrost]]
- [[projects/cipp]]
...

## Carry-Over Suggestions (Prioritized)
**High Priority (3+ days old):**
- [ ] Figure out why T20260415.0002 happened
- [ ] Liles Power Issues ticket: T20260127.0054

**Medium Priority (2 days old):**
- [ ] Datto SaaS Protection expiring check

**Recent (1 day old):**
- [ ] Ticket filter with merge confidence score
...

## Waiting-For Aging Check
| Item | Age | Status |
|------|-----|--------|
| ... | ... | ... |

---
*Generated: 2026-04-20 17:00*
*Source: 5 daily notes + 5 work-context files*
```

## Directory Structure

```
weekly-review/
├── src/weekly_review/         # Main package
│   ├── __init__.py
│   ├── __main__.py             # Entry point
│   ├── cli.py                  # Typer CLI
│   ├── parser.py               # Daily note + work-context parser
│   ├── extractor.py            # Content extraction (tasks, decisions, etc.)
│   ├── aggregator.py           # Merge/dedupe logic
│   ├── writer.py               # File/stdout output
│   ├── config.py               # Configuration handling
│   └── templates/              # Jinja2 templates
│       └── weekly_review.md.j2
├── tests/                      # Test suite
├── invoke.ps1                  # PowerShell wrapper
├── pyproject.toml              # Package config
├── README.md                   # This file
└── config.yaml                 # Default config
```

## How It Works

1. **Parser** reads daily notes and work-context files for the specified date range
2. **Extractor** identifies tasks, decisions, people, meetings, projects
3. **Aggregator** merges data from both sources with fuzzy deduplication
4. **Writer** generates markdown using Jinja2 templates
5. **CLI** provides convenient commands with rich progress display

## Integration with Daily Workflow

```
Monday-Friday: Daily notes captured in daily/*.md
              Work context synced to pages/work-context___*.md
              ↓
Friday PM:     Run weekly-review
              ↓
Output:        reviews/weekly/YYYY-W##.md
              ↓
Action:        Review, carry over tasks, update projects
```

## Requirements

- Python 3.10+
- Windows PowerShell 7+ (for wrapper)
- See `pyproject.toml` for Python dependencies

## License

AGPL-3.0
