"""Data models for weekly review."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from enum import Enum


class TaskStatus(Enum):
    """Task completion status."""
    COMPLETED = "completed"
    OPEN = "open"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """A task extracted from daily notes."""
    text: str
    status: TaskStatus
    source_file: str
    source_date: date
    priority: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    people: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    # For fuzzy deduplication
    normalized_text: str = ""
    # Age in days (for carry-over prioritization)
    age_days: int = 0
    # Whether this was carried over from a previous day
    is_carry_over: bool = False

    def __post_init__(self):
        if not self.normalized_text:
            self.normalized_text = self._normalize_text(self.text)

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for fuzzy matching."""
        # Remove brackets, lowercase, strip extra whitespace
        normalized = text.lower()
        # Remove Logseq links [[...]]
        normalized = normalized.replace("[[", "").replace("]]", "")
        # Remove common prefixes
        for prefix in ["- [ ] ", "- [x] ", "- [X] ", "- "]:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
        # Remove ticket numbers like T20260127.0054 for matching
        import re
        normalized = re.sub(r'\bt\d{8}\.\d{4}\b', '', normalized)
        # Compact whitespace
        normalized = ' '.join(normalized.split())
        return normalized.strip()


@dataclass
class Decision:
    """A decision or key note captured during the week."""
    text: str
    source_file: str
    source_date: date
    context: str = ""  # Surrounding context
    people: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class Person:
    """A person mentioned during the week."""
    name: str
    # Normalized name for deduplication
    normalized_name: str = ""
    mentions: list[dict] = field(default_factory=list)
    # Links to their page if available
    page_link: Optional[str] = None

    def __post_init__(self):
        if not self.normalized_name:
            self.normalized_name = self.name.lower().replace(" ", "")

    def add_mention(self, context: str, date: date, source_file: str):
        """Add a mention with context."""
        self.mentions.append({
            "context": context,
            "date": date,
            "source_file": source_file,
        })


@dataclass
class Meeting:
    """A meeting or time-blocked activity."""
    title: str
    date: date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    organizer: Optional[str] = None
    attendees: list[str] = field(default_factory=list)
    source_file: str = ""
    # Extracted from work context or daily notes
    is_from_calendar: bool = False
    is_from_worklog: bool = False


@dataclass
class Project:
    """A project referenced during the week."""
    name: str
    page_link: Optional[str] = None
    references: list[dict] = field(default_factory=list)
    tasks_count: int = 0
    completed_tasks_count: int = 0

    def add_reference(self, context: str, date: date, source_file: str):
        """Add a reference with context."""
        self.references.append({
            "context": context,
            "date": date,
            "source_file": source_file,
        })


@dataclass
class DailyNote:
    """Parsed daily note."""
    date: date
    file_path: str
    raw_content: str
    # Sections
    focus: list[str] = field(default_factory=list)
    next_actions: list[Task] = field(default_factory=list)
    work_log: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # Links extracted
    people: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    clients: list[str] = field(default_factory=list)


@dataclass
class WorkContext:
    """Parsed work context from Graph sync."""
    date: date
    file_path: str
    raw_content: str
    # Summary metrics
    calendar_items_count: int = 0
    sent_emails_count: int = 0
    completed_tasks_count: int = 0
    open_tasks_count: int = 0
    # Content
    calendar_events: list[dict] = field(default_factory=list)
    sent_emails: list[str] = field(default_factory=list)
    flagged_emails: list[str] = field(default_factory=list)
    completed_tasks: list[str] = field(default_factory=list)
    open_tasks: list[str] = field(default_factory=list)


@dataclass
class ExtractedContent:
    """All content extracted from a day's notes."""
    date: date
    tasks: list[Task] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    people: list[Person] = field(default_factory=list)
    meetings: list[Meeting] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    # Source info
    source_files: list[str] = field(default_factory=list)


@dataclass
class WeeklyReview:
    """Complete weekly review output."""
    # Week identification
    year: int
    week_number: int
    start_date: date
    end_date: date
    # Metrics
    days_with_entries: int = 0
    total_days: int = 7
    # Aggregated content
    completed_tasks: list[Task] = field(default_factory=list)
    open_tasks: list[Task] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    people: list[Person] = field(default_factory=list)
    meetings: list[Meeting] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    # Prioritized carry-overs
    carry_overs_high: list[Task] = field(default_factory=list)
    carry_overs_medium: list[Task] = field(default_factory=list)
    carry_overs_recent: list[Task] = field(default_factory=list)
    # Source info
    daily_notes_parsed: int = 0
    work_contexts_parsed: int = 0
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def week_string(self) -> str:
        """ISO week string like '2026-W16'."""
        return f"{self.year}-W{self.week_number:02d}"

    @property
    def date_range_string(self) -> str:
        """Human-readable date range."""
        return f"{self.start_date.strftime('%b %d')}-{self.end_date.strftime('%b %d')}"
