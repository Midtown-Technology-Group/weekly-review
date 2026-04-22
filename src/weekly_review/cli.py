"""CLI for weekly review generator."""

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from weekly_review.config import load_config, Config
from weekly_review.parser import parse_daily_notes, parse_work_contexts
from weekly_review.extractor import extract_all_content
from weekly_review.aggregator import create_weekly_review
from weekly_review.writer import write_weekly_review, generate_weekly_review_content
from weekly_review.models import WeeklyReview


app = typer.Typer(
    name="weekly-review",
    help="Automated GTD weekly review generator for Logseq knowledge graphs",
    rich_markup_mode="rich",
)
console = Console()


def parse_date_string(date_str: Optional[str]) -> Optional[date]:
    """Parse a date string in YYYY-MM-DD format."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise typer.BadParameter(f"Invalid date format: {date_str}. Use YYYY-MM-DD (e.g., 2026-04-15)")


def get_iso_week_dates(year: int, week: int) -> tuple[date, date]:
    """Get start and end dates for an ISO week."""
    # ISO week starts on Monday
    jan4 = date(year, 1, 4)
    start = jan4 + timedelta(weeks=week - 1, days=-jan4.weekday())
    end = start + timedelta(days=6)
    return start, end


def get_current_iso_week() -> tuple[int, int]:
    """Get current ISO year and week number."""
    today = date.today()
    iso_cal = today.isocalendar()
    return iso_cal.year, iso_cal.week


def parse_week_string(week_str: str) -> tuple[int, int]:
    """Parse ISO week string like '2026-W16'."""
    try:
        parts = week_str.upper().split("-W")
        year = int(parts[0])
        week = int(parts[1])
        return year, week
    except (IndexError, ValueError) as e:
        raise typer.BadParameter(f"Invalid week format: {week_str}. Use YYYY-W## (e.g., 2026-W16)")


def get_date_range(
    week: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    include_last_week: bool = False
) -> tuple[date, date]:
    """Determine date range from various input options."""
    if week:
        year, week_num = parse_week_string(week)
        week_start, week_end = get_iso_week_dates(year, week_num)

        if include_last_week:
            # Extend to include previous week
            week_start = week_start - timedelta(days=7)

        return week_start, week_end

    if start_date and end_date:
        if include_last_week:
            start_date = start_date - timedelta(days=7)
        return start_date, end_date

    if start_date:
        # Single week from start date
        end_date = start_date + timedelta(days=6)
        if include_last_week:
            start_date = start_date - timedelta(days=7)
        return start_date, end_date

    # Default to current week
    year, week_num = get_current_iso_week()
    week_start, week_end = get_iso_week_dates(year, week_num)

    if include_last_week:
        week_start = week_start - timedelta(days=7)

    return week_start, week_end


def generate_date_range(start: date, end: date) -> list[date]:
    """Generate list of dates from start to end inclusive."""
    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    return dates


@app.command()
def generate(
    week: Optional[str] = typer.Argument(
        None,
        help="ISO week to generate for (e.g., '2026-W16'). Defaults to current week."
    ),
    start_date: Optional[str] = typer.Option(
        None, "--start-date", "-s",
        help="Start date in YYYY-MM-DD format (overrides week)",
    ),
    end_date: Optional[str] = typer.Option(
        None, "--end-date", "-e",
        help="End date in YYYY-MM-DD format (requires --start-date)",
    ),
    include_last_week: bool = typer.Option(
        False, "--include-last-week", "-l",
        help="Include previous week for comparison"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d",
        help="Preview to stdout, don't write file"
    ),
    output_path: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Custom output path (default: reviews/weekly/YYYY-W##.md)"
    ),
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c",
        help="Path to config file (default: auto-discover)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Verbose output"
    ),
) -> None:
    """Generate weekly review for specified week or date range."""
    # Parse date strings
    start_date_parsed = parse_date_string(start_date)
    end_date_parsed = parse_date_string(end_date)

    # Load configuration
    if config_path:
        config = load_config(config_path.parent)
    else:
        config = load_config()

    # Determine date range
    week_start, week_end = get_date_range(week, start_date_parsed, end_date_parsed, include_last_week)
    date_range = generate_date_range(week_start, week_end)

    # Determine week string for output
    if week:
        year, week_num = parse_week_string(week)
    else:
        # Use the ISO week of the end date (or middle of range)
        mid_date = week_start + timedelta(days=(week_end - week_start).days // 2)
        iso_cal = mid_date.isocalendar()
        year, week_num = iso_cal.year, iso_cal.week

    week_string = f"{year}-W{week_num:02d}"
    date_range_str = f"{week_start.strftime('%b %d')}-{week_end.strftime('%b %d')}"

    console.print(f"[bold blue]Weekly Review Generator[/bold blue]")
    console.print(f"Week: [cyan]{week_string}[/cyan] ({date_range_str})")
    console.print(f"Date range: [dim]{week_start} to {week_end}[/dim]")
    console.print(f"Daily notes: [dim]{config.get_daily_notes_dir()}[/dim]")
    console.print(f"Work context: [dim]{config.get_work_context_dir()}[/dim]")
    console.print()

    # Parse files with simple progress messages
    console.print("Parsing daily notes...", style="cyan")
    daily_notes = parse_daily_notes(date_range, config.get_daily_notes_dir())

    console.print("Parsing work context...", style="cyan")
    work_contexts = parse_work_contexts(date_range, config.get_work_context_dir())

    console.print("Extracting content...", style="cyan")
    contents = extract_all_content(daily_notes, work_contexts)

    console.print("Aggregating and deduplicating...", style="cyan")
    review = create_weekly_review(
        contents=contents,
        week_start=week_start,
        week_end=week_end,
        year=year,
        week_number=week_num,
        config=config,
        daily_notes_count=len(daily_notes),
        work_contexts_count=len(work_contexts)
    )

    # Show summary
    console.print()
    console.print("[bold green][OK] Generated weekly review[/bold green]")
    console.print()

    table = Table(title="Summary", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right")

    table.add_row("Days with entries", f"{review.days_with_entries}/{review.total_days}")
    table.add_row("Completed tasks", str(len(review.completed_tasks)))
    table.add_row("Open tasks", str(len(review.open_tasks)))
    table.add_row("Unique people", str(len(review.people)))
    table.add_row("Meetings", str(len(review.meetings)))
    table.add_row("Decisions", str(len(review.decisions)))
    table.add_row("Projects", str(len(review.projects)))

    if review.carry_overs_high:
        table.add_row("High priority carry-overs", str(len(review.carry_overs_high)), style="red")
    if review.carry_overs_medium:
        table.add_row("Medium priority carry-overs", str(len(review.carry_overs_medium)), style="yellow")

    console.print(table)
    console.print()

    # Write output
    output_file = write_weekly_review(review, config, output_path, dry_run)

    if dry_run:
        console.print("[dim]--- Preview (dry run) ---[/dim]")
        console.print(generate_weekly_review_content(review, config))
        console.print("[dim]--- End preview ---[/dim]")
    else:
        console.print(f"[green]Output written to:[/green] {output_file}")
        console.print()
        console.print("[dim]Next steps:[/dim]")
        console.print("  1. Review the generated markdown")
        console.print("  2. Add any missing context")
        console.print("  3. Update project pages with progress")
        console.print("  4. Carry over high priority tasks")


@app.command()
def config(
    init: bool = typer.Option(
        False, "--init",
        help="Create a new config file in current directory"
    ),
    show: bool = typer.Option(
        False, "--show", "-s",
        help="Show current configuration"
    ),
) -> None:
    """Manage configuration."""
    if init:
        from weekly_review.config import init_config
        config_path = init_config(Path("weekly-review.yaml"))
        console.print(f"[green]Created config file:[/green] {config_path}")
        return

    # Load and show current config
    cfg = load_config()

    if show:
        console.print("[bold]Current Configuration:[/bold]")
        console.print(f"  Knowledge graph root: [cyan]{cfg.knowledge_graph_root}[/cyan]")
        console.print(f"  Daily notes path: [cyan]{cfg.daily_notes_path}[/cyan]")
        console.print(f"  Work context path: [cyan]{cfg.work_context_path}[/cyan]")
        console.print(f"  Output path: [cyan]{cfg.output_path}[/cyan]")
        console.print(f"  Fuzzy threshold: [cyan]{cfg.fuzzy_threshold}[/cyan]")
        console.print(f"  Template: [cyan]{cfg.template}[/cyan]")
    else:
        console.print("[dim]Use --show to display configuration or --init to create a new config file[/dim]")


@app.command()
def preview(
    week: Optional[str] = typer.Argument(None, help="Week to preview (e.g., '2026-W16')"),
) -> None:
    """Quick preview of what would be generated (alias for generate --dry-run)."""
    # Call generate with dry_run=True
    generate(week=week, dry_run=True)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
