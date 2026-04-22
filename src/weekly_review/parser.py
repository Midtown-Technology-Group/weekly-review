"""Parser for daily notes and work context files."""

import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from weekly_review.models import DailyNote, WorkContext, Task, TaskStatus


class DailyNoteParser:
    """Parser for Logseq daily notes."""

    # Patterns for extracting different sections
    DATE_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")

    # Task patterns
    TASK_DONE_PATTERN = re.compile(r"^- \[([xX])\] (.+)$", re.MULTILINE)
    TASK_OPEN_PATTERN = re.compile(r"^- \[ \] (.+)$", re.MULTILINE)
    TASK_CANCELLED_PATTERN = re.compile(r"^- \[-\] (.+)$", re.MULTILINE)

    # Link patterns
    LINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")
    LINK_WITH_ALIAS_PATTERN = re.compile(r"\[([^\]]+)\]\[\[([^\]]+)\]\]")
    LINK_WITH_ALT_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    # Section headers
    FOCUS_HEADER_PATTERN = re.compile(r"^#{1,2}[^#]*(?:[Ff]ocus|FOCUS)[^#]*$", re.MULTILINE)
    WORK_LOG_HEADER_PATTERN = re.compile(r"^#{1,2}[^#]*(?:[Ww]ork\s*[Ll]og|WORK\s*LOG)[^#]*$", re.MULTILINE)
    NOTES_HEADER_PATTERN = re.compile(r"^#{1,2}[^#]*(?:[Nn]otes|NOTES)[^#]*$", re.MULTILINE)
    LINKS_HEADER_PATTERN = re.compile(r"^#{1,2}[^#]*(?:[Ll]inks|LINKS)[^#]*$", re.MULTILINE)
    NEXT_ACTIONS_HEADER_PATTERN = re.compile(r"^#{1,2}[^#]*(?:[Nn]ext\s*[Aa]ctions|NEXT\s*ACTIONS)[^#]*$", re.MULTILINE)

    # Time log pattern (e.g., "9:37 to 10:00 Call with Mike")
    TIME_LOG_PATTERN = re.compile(
        r"^(\d{1,2}):(\d{2})(?::\d{2})?(?:\s*(?:to|[-–])\s*(\d{1,2}):(\d{2})(?::\d{2})?)?\s*(.+)$",
        re.MULTILINE
    )

    # Decision indicators
    DECISION_KEYWORDS = [
        "decided", "decision", "agreed", "concluded", "resolved",
        "standard", "policy", "rule", "implemented", "deployed",
        "changed", "updated", "migrated", "fixed", "disabled", "enabled"
    ]

    def parse(self, file_path: Path) -> Optional[DailyNote]:
        """Parse a daily note file."""
        if not file_path.exists():
            return None

        # Extract date from filename
        note_date = self._extract_date_from_filename(file_path.name)
        if not note_date:
            return None

        # Read content
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        note = DailyNote(
            date=note_date,
            file_path=str(file_path),
            raw_content=content,
        )

        # Parse sections
        note.focus = self._extract_focus(content)
        note.next_actions = self._extract_next_actions(content, note_date, str(file_path))
        note.work_log = self._extract_work_log(content)
        note.notes = self._extract_notes(content)

        # Extract links
        all_links = self._extract_all_links(content)
        note.people = self._filter_people_links(all_links)
        note.projects = self._filter_project_links(all_links)
        note.topics = self._filter_topic_links(all_links)
        note.clients = self._filter_client_links(all_links)

        return note

    def _extract_date_from_filename(self, filename: str) -> Optional[date]:
        """Extract date from filename like '2026-04-22.md'."""
        match = self.DATE_PATTERN.match(filename)
        if match:
            year, month, day = map(int, match.groups())
            return date(year, month, day)
        return None

    def _extract_section(self, content: str, header_pattern: re.Pattern, next_header_pattern: Optional[re.Pattern] = None) -> str:
        """Extract content between a header and the next header or end."""
        match = header_pattern.search(content)
        if not match:
            return ""

        start = match.end()

        # Find next section header or end
        remaining = content[start:]
        if next_header_pattern:
            next_match = next_header_pattern.search(remaining)
            if next_match:
                return remaining[:next_match.start()]

        return remaining

    def _extract_focus(self, content: str) -> list[str]:
        """Extract focus items."""
        section = self._extract_section(content, self.FOCUS_HEADER_PATTERN, self.NEXT_ACTIONS_HEADER_PATTERN)
        return [line.strip("- ") for line in section.split("\n") if line.strip().startswith("-")]

    def _extract_next_actions(self, content: str, note_date: date, file_path: str) -> list[Task]:
        """Extract next actions (open tasks)."""
        # Look for next actions section
        section = self._extract_section(content, self.NEXT_ACTIONS_HEADER_PATTERN, self.WORK_LOG_HEADER_PATTERN)

        tasks = []
        for match in self.TASK_OPEN_PATTERN.finditer(content):
            task_text = match.group(1).strip()
            tasks.append(Task(
                text=task_text,
                status=TaskStatus.OPEN,
                source_file=file_path,
                source_date=note_date,
            ))

        return tasks

    def _extract_work_log(self, content: str) -> list[str]:
        """Extract work log entries."""
        section = self._extract_section(content, self.WORK_LOG_HEADER_PATTERN, self.NOTES_HEADER_PATTERN)

        entries = []
        for line in section.split("\n"):
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("\t-")):
                # Clean up the entry
                entry = line.lstrip("-\t ")
                if entry:
                    entries.append(entry)

        return entries

    def _extract_notes(self, content: str) -> list[str]:
        """Extract notes/decisions from the notes section."""
        section = self._extract_section(content, self.NOTES_HEADER_PATTERN, self.LINKS_HEADER_PATTERN)

        notes = []
        for line in section.split("\n"):
            line = line.strip()
            if line and line.startswith("-"):
                note = line.lstrip("- ")
                if note:
                    notes.append(note)

        return notes

    def _extract_all_links(self, content: str) -> list[str]:
        """Extract all [[links]] from content."""
        links = []

        # Standard [[link]] format
        for match in self.LINK_PATTERN.finditer(content):
            links.append(match.group(1))

        # [alias][[link]] format
        for match in self.LINK_WITH_ALIAS_PATTERN.finditer(content):
            links.append(match.group(2))

        return links

    def _filter_people_links(self, links: list[str]) -> list[str]:
        """Filter links that appear to be people."""
        people = []
        for link in links:
            # People often in people/ namespace or common first names
            if link.startswith("people/") or link.startswith("people."):
                people.append(link)
            elif " " in link and not "/" in link:
                # Names typically have spaces and no slashes
                # Additional heuristics: check for common name patterns
                if self._looks_like_person_name(link):
                    people.append(link)
        return list(set(people))

    def _filter_project_links(self, links: list[str]) -> list[str]:
        """Filter links that appear to be projects."""
        projects = []
        for link in links:
            if link.startswith("projects/") or link.startswith("projects."):
                projects.append(link)
        return list(set(projects))

    def _filter_topic_links(self, links: list[str]) -> list[str]:
        """Filter links that appear to be topics."""
        topics = []
        for link in links:
            # Topics are usually single words or simple phrases without namespace
            if "/" not in link and "." not in link:
                if link not in ["now", "later", "todo", "done"]:
                    topics.append(link)
        return list(set(topics))

    def _filter_client_links(self, links: list[str]) -> list[str]:
        """Filter links that appear to be clients."""
        clients = []
        for link in links:
            # Clients might have specific patterns or be in people namespace
            if "client" in link.lower() or "customer" in link.lower():
                clients.append(link)
        return list(set(clients))

    def _looks_like_person_name(self, text: str) -> bool:
        """Heuristic to check if text looks like a person's name."""
        # Skip common non-person patterns
        skip_patterns = [
            "template", "config", "setup", "guide", "doc", "api",
            "script", "tool", "app", "system", "process", "workflow",
            "meeting", "call", "review", "report", "analysis"
        ]

        text_lower = text.lower()
        for pattern in skip_patterns:
            if pattern in text_lower:
                return False

        # Names typically have 2-4 words, each capitalized
        words = text.split()
        if len(words) < 1 or len(words) > 5:
            return False

        return True


class WorkContextParser:
    """Parser for work context files from Graph sync."""

    DATE_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")

    def parse(self, file_path: Path) -> Optional[WorkContext]:
        """Parse a work context file."""
        if not file_path.exists():
            return None

        # Extract date from filename (work-context___2026-04-22.md)
        note_date = self._extract_date_from_filename(file_path.name)
        if not note_date:
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        ctx = WorkContext(
            date=note_date,
            file_path=str(file_path),
            raw_content=content,
        )

        # Parse summary metrics
        ctx.calendar_items_count = self._extract_count(content, "Calendar items")
        ctx.sent_emails_count = self._extract_count(content, "Sent email items")
        ctx.completed_tasks_count = self._extract_count(content, "Completed tasks today")
        ctx.open_tasks_count = self._extract_count(content, "Open tasks in focus")

        # Parse content sections
        ctx.calendar_events = self._extract_calendar_events(content)
        ctx.sent_emails = self._extract_list_section(content, "Sent Email")
        ctx.flagged_emails = self._extract_list_section(content, "Flagged / Important Email")
        ctx.completed_tasks = self._extract_list_section(content, "Completed today")
        ctx.open_tasks = self._extract_list_section(content, "Open / in focus")

        return ctx

    def _extract_date_from_filename(self, filename: str) -> Optional[date]:
        """Extract date from filename like 'work-context___2026-04-22.md'."""
        match = self.DATE_PATTERN.search(filename)
        if match:
            year, month, day = map(int, match.groups())
            return date(year, month, day)
        return None

    def _extract_count(self, content: str, label: str) -> int:
        """Extract a count value from summary section."""
        pattern = re.compile(rf"- {re.escape(label)}:\s*(\d+)", re.IGNORECASE)
        match = pattern.search(content)
        if match:
            return int(match.group(1))
        return 0

    def _extract_list_section(self, content: str, section_name: str) -> list[str]:
        """Extract items from a list section."""
        # Find the section header
        pattern = re.compile(rf"^##\s*{re.escape(section_name)}.*$", re.MULTILINE | re.IGNORECASE)
        match = pattern.search(content)
        if not match:
            return []

        # Get content until next section
        start = match.end()
        next_section = re.compile(r"^##\s*", re.MULTILINE)
        remaining = content[start:]
        next_match = next_section.search(remaining)

        if next_match:
            section_content = remaining[:next_match.start()]
        else:
            section_content = remaining

        # Extract list items
        items = []
        for line in section_content.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                item = line.lstrip("-* ")
                if item and item != "(No items)":
                    items.append(item)

        return items

    def _extract_calendar_events(self, content: str) -> list[dict]:
        """Extract calendar events."""
        section = self._extract_list_section(content, "Calendar")
        events = []

        for item in section:
            # Parse format like "09:00-09:30 Team standup | organizer: Manager"
            event = {"raw": item}

            # Try to extract time range
            time_match = re.match(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})\s*(.+)", item)
            if time_match:
                event["start_time"] = f"{time_match.group(1)}:{time_match.group(2)}"
                event["end_time"] = f"{time_match.group(3)}:{time_match.group(4)}"
                event["title"] = time_match.group(5).split("|")[0].strip()

                # Extract organizer if present
                if "|" in item:
                    organizer_match = re.search(r"organizer:\s*([^|]+)", item)
                    if organizer_match:
                        event["organizer"] = organizer_match.group(1).strip()

            events.append(event)

        return events


def parse_daily_notes(date_range: list[date], daily_notes_dir: Path) -> list[DailyNote]:
    """Parse all daily notes for a date range."""
    parser = DailyNoteParser()
    notes = []

    for note_date in date_range:
        filename = f"{note_date}.md"
        file_path = daily_notes_dir / filename

        note = parser.parse(file_path)
        if note:
            notes.append(note)

    return notes


def parse_work_contexts(date_range: list[date], work_context_dir: Path) -> list[WorkContext]:
    """Parse all work context files for a date range."""
    parser = WorkContextParser()
    contexts = []

    for ctx_date in date_range:
        # Try both naming conventions
        filenames = [
            f"work-context___{ctx_date}.md",
            f"work-context.daily.{ctx_date}.md",
            f"work-context_{ctx_date}.md",
        ]

        for filename in filenames:
            file_path = work_context_dir / filename
            ctx = parser.parse(file_path)
            if ctx:
                contexts.append(ctx)
                break

    return contexts
