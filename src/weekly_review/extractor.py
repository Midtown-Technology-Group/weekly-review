"""Content extraction from parsed notes."""

import re
from datetime import date
from typing import Optional

from weekly_review.models import (
    DailyNote,
    WorkContext,
    ExtractedContent,
    Task,
    TaskStatus,
    Decision,
    Person,
    Meeting,
    Project,
)


class ContentExtractor:
    """Extract structured content from daily notes and work contexts."""

    # Decision indicators in text
    DECISION_PATTERNS = [
        r"(?i)(?:decided|decision)\s+(?:to|on|that)\s+(.+)",
        r"(?i)(?:agreed|concluded)\s+(?:to|on|that)\s+(.+)",
        r"(?i)(?:resolved)\s+(?:to|that)\s+(.+)",
        r"(?i)(?:implemented|deployed|migrated)\s+(.+)",
        r"(?i)(?:standard)\s+(?:to|for)\s+(.+)",
        r"(?i)(?:changed?|updated?)\s+(.+?)(?:\s+(?:to|from|for))",
        r"(?i)(?:disabled?|enabled?)\s+(.+)",
        r"(?i)(?:fixed)\s+(.+)",
    ]

    # People names to watch for (common patterns)
    PEOPLE_INDICATORS = [
        r"(?i)with\s+\[\[([^\]]+)\]\]",
        r"(?i)talked to\s+\[\[([^\]]+)\]\]",
        r"(?i)call with\s+\[\[([^\]]+)\]\]",
        r"(?i)chat with\s+\[\[([^\]]+)\]\]",
        r"(?i)from\s+\[\[([^\]]+)\]\]",
        r"(?i)to\s+\[\[([^\]]+)\]\]",
    ]

    # Meeting patterns in work log
    MEETING_PATTERNS = [
        r"(?i)(\d{1,2}:\d{2})\s*(?:to|-)\s*(\d{1,2}:\d{2})\s*(?:call|meeting|sync|standup)\s+with\s+(.+)",
        r"(?i)(\d{1,2}:\d{2})\s*(?:to|-)\s*(\d{1,2}:\d{2})\s*(.+)",
        r"(?i)call\s+with\s+\[\[([^\]]+)\]\]",
        r"(?i)meeting\s+with\s+\[\[([^\]]+)\]\]",
    ]

    def __init__(self):
        self.decision_regexes = [re.compile(p) for p in self.DECISION_PATTERNS]
        self.people_regexes = [re.compile(p) for p in self.PEOPLE_INDICATORS]
        self.meeting_regexes = [re.compile(p) for p in self.MEETING_PATTERNS]

    def extract_from_daily_note(self, note: DailyNote) -> ExtractedContent:
        """Extract all content from a daily note."""
        content = ExtractedContent(date=note.date, source_files=[note.file_path])

        # Extract tasks from next actions
        content.tasks.extend(note.next_actions)

        # Extract completed tasks from work log
        content.tasks.extend(self._extract_completed_tasks_from_worklog(note))

        # Extract decisions from notes
        content.decisions.extend(self._extract_decisions_from_notes(note))

        # Extract people
        content.people.extend(self._extract_people(note))

        # Extract meetings
        content.meetings.extend(self._extract_meetings_from_worklog(note))

        # Extract projects
        content.projects.extend(self._extract_projects(note))

        # Extract topics
        content.topics.extend(note.topics)

        return content

    def extract_from_work_context(self, ctx: WorkContext) -> ExtractedContent:
        """Extract content from a work context file."""
        content = ExtractedContent(date=ctx.date, source_files=[ctx.file_path])

        # Extract tasks from completed list
        for task_text in ctx.completed_tasks:
            content.tasks.append(Task(
                text=task_text,
                status=TaskStatus.COMPLETED,
                source_file=ctx.file_path,
                source_date=ctx.date,
            ))

        # Extract tasks from open list
        for task_text in ctx.open_tasks:
            content.tasks.append(Task(
                text=task_text,
                status=TaskStatus.OPEN,
                source_file=ctx.file_path,
                source_date=ctx.date,
            ))

        # Extract meetings from calendar events
        for event in ctx.calendar_events:
            meeting = Meeting(
                title=event.get("title", event.get("raw", "")),
                date=ctx.date,
                start_time=event.get("start_time"),
                end_time=event.get("end_time"),
                organizer=event.get("organizer"),
                source_file=ctx.file_path,
                is_from_calendar=True,
            )
            # Calculate duration if times available
            if meeting.start_time and meeting.end_time:
                meeting.duration_minutes = self._calculate_duration(
                    meeting.start_time, meeting.end_time
                )
            content.meetings.append(meeting)

        # Extract people from calendar organizers
        for event in ctx.calendar_events:
            if event.get("organizer"):
                person = Person(name=event["organizer"])
                person.add_mention(
                    f"Organizer: {event.get('title', '')}",
                    ctx.date,
                    ctx.file_path
                )
                content.people.append(person)

        return content

    def _extract_completed_tasks_from_worklog(self, note: DailyNote) -> list[Task]:
        """Look for completed task indicators in work log."""
        tasks = []
        completed_indicators = [
            r"(?i)(?:completed?|finished?|done|wrapped up)\s+(.+)",
            r"(?i)(?:got\s+(.+?)\s+(?:done|working|fixed|deployed))",
            r"(?i)(?:fixed|resolved|closed)\s+(.+)",
        ]

        for entry in note.work_log:
            for pattern in completed_indicators:
                match = re.search(pattern, entry)
                if match:
                    task_text = match.group(1).strip()
                    # Clean up the text
                    task_text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', task_text)
                    tasks.append(Task(
                        text=task_text,
                        status=TaskStatus.COMPLETED,
                        source_file=note.file_path,
                        source_date=note.date,
                    ))
                    break

        return tasks

    def _extract_decisions_from_notes(self, note: DailyNote) -> list[Decision]:
        """Extract decisions and key notes from notes section."""
        decisions = []

        for note_text in note.notes:
            # Check if it looks like a decision
            is_decision = False
            for pattern in self.decision_regexes:
                if pattern.search(note_text):
                    is_decision = True
                    break

            # Also capture notes that look significant (contain project or key terms)
            if not is_decision:
                key_terms = ["standard", "policy", "implemented", "deployed",
                           "changed", "updated", "migrated", "fixed"]
                if any(term in note_text.lower() for term in key_terms):
                    is_decision = True

            if is_decision:
                # Extract links
                people = self._extract_links_of_type(note_text, "people")
                projects = self._extract_links_of_type(note_text, "projects")

                decisions.append(Decision(
                    text=note_text,
                    source_file=note.file_path,
                    source_date=note.date,
                    people=people,
                    projects=projects,
                ))

        return decisions

    def _extract_people(self, note: DailyNote) -> list[Person]:
        """Extract people mentioned in the daily note."""
        people_map: dict[str, Person] = {}

        # Extract from explicit people links
        for person_link in note.people:
            # Clean up the link
            name = person_link.replace("people/", "").replace("people.", "")
            if name not in people_map:
                people_map[name] = Person(name=name, page_link=person_link)

        # Extract from work log mentions
        for entry in note.work_log:
            for pattern in self.people_regexes:
                for match in pattern.finditer(entry):
                    name = match.group(1)
                    if name not in people_map:
                        people_map[name] = Person(name=name)
                    people_map[name].add_mention(entry, note.date, note.file_path)

        return list(people_map.values())

    def _extract_meetings_from_worklog(self, note: DailyNote) -> list[Meeting]:
        """Extract meetings from work log entries."""
        meetings = []

        for entry in note.work_log:
            # Try time-based patterns first
            time_match = re.match(
                r"(\d{1,2}:\d{2})\s+(?:to|-|–)\s+(\d{1,2}:\d{2})\s+(.+)",
                entry
            )

            if time_match:
                start_time = time_match.group(1)
                end_time = time_match.group(2)
                description = time_match.group(3)

                # Determine if this is a meeting
                is_meeting = any(term in description.lower()
                               for term in ["call", "meeting", "sync", "talked",
                                          "with", "discussion"])

                # Extract people mentioned
                people = re.findall(r"\[\[([^\]]+)\]\]", description)

                meeting = Meeting(
                    title=description,
                    date=note.date,
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=self._calculate_duration(start_time, end_time),
                    attendees=people,
                    source_file=note.file_path,
                    is_from_worklog=True,
                )
                meetings.append(meeting)
            else:
                # Try non-time patterns
                if "call with" in entry.lower() or "meeting with" in entry.lower():
                    people = re.findall(r"\[\[([^\]]+)\]\]", entry)
                    if people:
                        meetings.append(Meeting(
                            title=entry,
                            date=note.date,
                            attendees=people,
                            source_file=note.file_path,
                            is_from_worklog=True,
                        ))

        return meetings

    def _extract_projects(self, note: DailyNote) -> list[Project]:
        """Extract projects referenced in the daily note."""
        projects_map: dict[str, Project] = {}

        for project_link in note.projects:
            name = project_link.replace("projects/", "").replace("projects.", "")
            if name not in projects_map:
                projects_map[name] = Project(
                    name=name,
                    page_link=project_link
                )

        # Also look for project mentions in work log
        for entry in note.work_log:
            for match in re.finditer(r"\[\[projects/([^\]]+)\]\]", entry):
                name = match.group(1)
                if name not in projects_map:
                    projects_map[name] = Project(
                        name=name,
                        page_link=f"projects/{name}"
                    )
                projects_map[name].add_reference(entry, note.date, note.file_path)

        return list(projects_map.values())

    def _extract_links_of_type(self, text: str, link_type: str) -> list[str]:
        """Extract links of a specific type from text."""
        pattern = rf"\[\[{link_type}/([^\]]+)\]\]"
        return re.findall(pattern, text)

    def _calculate_duration(self, start_time: str, end_time: str) -> Optional[int]:
        """Calculate duration in minutes between two time strings."""
        try:
            def parse_time(t: str) -> int:
                parts = t.split(":")
                hours = int(parts[0])
                minutes = int(parts[1])
                return hours * 60 + minutes

            start_minutes = parse_time(start_time)
            end_minutes = parse_time(end_time)

            # Handle crossing midnight (unlikely for work, but just in case)
            if end_minutes < start_minutes:
                end_minutes += 24 * 60

            return end_minutes - start_minutes
        except Exception:
            return None


def extract_all_content(
    daily_notes: list[DailyNote],
    work_contexts: list[WorkContext]
) -> list[ExtractedContent]:
    """Extract content from all sources and group by date."""
    extractor = ContentExtractor()

    # Group by date
    content_by_date: dict[date, ExtractedContent] = {}

    for note in daily_notes:
        if note.date not in content_by_date:
            content_by_date[note.date] = ExtractedContent(date=note.date)
        extracted = extractor.extract_from_daily_note(note)
        content_by_date[note.date] = _merge_content(content_by_date[note.date], extracted)

    for ctx in work_contexts:
        if ctx.date not in content_by_date:
            content_by_date[ctx.date] = ExtractedContent(date=ctx.date)
        extracted = extractor.extract_from_work_context(ctx)
        content_by_date[ctx.date] = _merge_content(content_by_date[ctx.date], extracted)

    return list(content_by_date.values())


def _merge_content(existing: ExtractedContent, new: ExtractedContent) -> ExtractedContent:
    """Merge two ExtractedContent objects."""
    existing.tasks.extend(new.tasks)
    existing.decisions.extend(new.decisions)
    existing.people.extend(new.people)
    existing.meetings.extend(new.meetings)
    existing.projects.extend(new.projects)
    existing.topics.extend(new.topics)
    existing.source_files.extend(new.source_files)
    return existing
