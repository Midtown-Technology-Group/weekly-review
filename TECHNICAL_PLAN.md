# Weekly Review Generator - Technical Plan

## Overview
Automated GTD weekly review generator for Logseq knowledge graphs. Parses `daily/*.md` and `pages/work-context___*.md` files to generate comprehensive weekly summaries.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Entry (cli.py)                        │
│                     Typer-based command line                       │
├─────────────────────────────────────────────────────────────────┤
│                        Orchestration Flow                        │
│  1. Parse arguments → Date range → Config loading                │
│  2. Parse daily notes → DailyNote[]                              │
│  3. Parse work contexts → WorkContext[]                          │
│  4. Extract content → ExtractedContent[]                         │
│  5. Aggregate & dedupe → WeeklyReview                            │
│  6. Generate markdown → Write file                               │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐          ┌──────────┐          ┌──────────┐
   │ parser  │          │ extractor│          │aggregator│
   │  .py    │          │  .py     │          │  .py     │
   ├─────────┤          ├──────────┤          ├──────────┤
   │DailyNote│          │  Task    │          │ Fuzzy    │
   │WorkCtx  │          │Decision  │          │ Dedupe   │
   │ Parser  │          │ Person   │          │ Priority │
   └─────────┘          │ Meeting  │          │ Sorting  │
                        │ Project  │          └──────────┘
                        └──────────┘
                              │
                              ▼
                        ┌──────────┐
                        │ writer.py│
                        │  Jinja2  │
                        │ Template │
                        └──────────┘
```

## Components

### 1. Parser (`parser.py`)
- `DailyNoteParser`: Parses Logseq daily notes
  - Extracts: focus, next actions, work log, notes
  - Identifies links: people, projects, topics, clients
  - Task patterns: `- [ ]`, `- [x]`, `- [-]`
- `WorkContextParser`: Parses Graph sync work context
  - Extracts: calendar events, emails, tasks
  - Summary metrics counting

### 2. Extractor (`extractor.py`)
- `ContentExtractor`: Extracts structured content
  - Tasks (completed/open)
  - Decisions (keywords: decided, implemented, fixed, etc.)
  - People (from [[links]] and context)
  - Meetings (time-parsed from work log)
  - Projects (namespace filtering)

### 3. Aggregator (`aggregator.py`)
- `FuzzyAggregator`: Deduplication using `thefuzz`
  - Task deduplication (normalized text + fuzzy ratio)
  - Decision deduplication
  - Meeting deduplication (same day + similar title)
  - People merging (mention aggregation)
  - Project reference merging
- Carry-over prioritization (age-based thresholds)

### 4. Writer (`writer.py`)
- `WeeklyReviewWriter`: Markdown generation
  - Built-in Jinja2 template
  - Custom template support
  - File/stdout output

### 5. CLI (`cli.py`)
- Typer-based commands:
  - `generate`: Main review generation
  - `config`: Configuration management
  - `preview`: Dry-run preview
- Rich progress display and tables
- ISO week support (YYYY-W##)

### 6. Config (`config.py`)
- YAML-based configuration
- Auto-discovery (walks up directories)
- Path resolution relative to knowledge graph root

## Data Models

```python
@dataclass
class WeeklyReview:
    year: int
    week_number: int
    start_date: date
    end_date: date
    completed_tasks: list[Task]
    open_tasks: list[Task]
    carry_overs_high: list[Task]      # 3+ days
    carry_overs_medium: list[Task]    # 2 days
    carry_overs_recent: list[Task]    # 1 day
    decisions: list[Decision]
    people: list[Person]
    meetings: list[Meeting]
    projects: list[Project]
```

## Fuzzy Matching Strategy

1. **Normalization**: Remove brackets, lowercase, strip ticket numbers
2. **Threshold**: Configurable (default 85/100)
3. **Comparison**: `fuzz.ratio()` from `thefuzz`
4. **Short-circuit**: Exact match first, then fuzzy

Example:
```python
"Review CIPP deployment configuration"
"Review CIPP deployment config"
# → 95% match (duplicate)
```

## Output Format

Generated: `reviews/weekly/YYYY-W##.md`

Sections:
1. Week at a Glance (metrics table)
2. Completed This Week
3. Key Decisions & Notes
4. People This Week
5. Meetings & Time Blocks
6. Active Projects
7. Carry-Over Suggestions (prioritized)
8. Waiting-For Aging Check
9. Weekly Reflection prompts
10. Next Week Preview

## Dependencies

```
typer>=0.12.0          # CLI framework
rich>=13.0.0           # Terminal UI
jinja2>=3.1.0          # Templating
thefuzz>=0.22.0        # Fuzzy matching
python-Levenshtein>=0.25.0  # Speedup for thefuzz
pydantic>=2.0.0        # Data validation
pydantic-settings>=2.0.0
python-dateutil>=2.8.0  # Date parsing
pyyaml>=6.0            # Config files
```

## Usage Patterns

### Standard Weekly Review (Friday)
```powershell
.\weekly-review\invoke.ps1
```

### Specific Week
```powershell
.\weekly-review\invoke.ps1 -Week "2026-W16"
```

### Custom Range
```powershell
.\weekly-review\invoke.ps1 -StartDate "2026-04-14" -EndDate "2026-04-20"
```

### With Context from Last Week
```powershell
.\weekly-review\invoke.ps1 -IncludeLastWeek
```

### Preview Only
```powershell
.\weekly-review\invoke.ps1 -DryRun
```

## Integration with work-context-sync

Same pattern:
- PowerShell wrapper (`invoke.ps1`)
- Venv activation
- PYTHONPATH handling
- Exit code propagation

## File Structure

```
weekly-review/
├── src/weekly_review/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── parser.py
│   ├── extractor.py
│   ├── aggregator.py
│   ├── writer.py
│   ├── config.py
│   ├── models.py
│   └── templates/
│       ├── __init__.py
│       └── weekly_review.md.j2
├── tests/
│   ├── conftest.py
│   ├── __init__.py
│   └── test_weekly_review.py
├── pyproject.toml
├── config.yaml
├── README.md
└── invoke.ps1
```

## Testing

Run tests:
```powershell
cd weekly-review
.\.venv\Scripts\Activate.ps1
pytest tests/ -v
```

## Future Enhancements

1. Trend analysis (compare week-over-week)
2. Integration with Logseq queries
3. Export to other formats (PDF, HTML)
4. Web interface
5. Automated scheduling
6. Integration with timesheet systems
