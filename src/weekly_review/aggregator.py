"""Aggregator with fuzzy matching for deduplication."""

from datetime import date
from typing import Optional

from thefuzz import fuzz, process

from weekly_review.models import (
    Task,
    Decision,
    Person,
    Meeting,
    Project,
    ExtractedContent,
    WeeklyReview,
    TaskStatus,
)
from weekly_review.config import Config


class FuzzyAggregator:
    """Aggregate and deduplicate content using fuzzy matching."""

    def __init__(self, config: Config):
        self.config = config
        self.fuzzy_threshold = config.fuzzy_threshold

    def aggregate(
        self,
        contents: list[ExtractedContent],
        week_start: date,
        week_end: date,
        year: int,
        week_number: int
    ) -> WeeklyReview:
        """Aggregate all content into a weekly review."""
        review = WeeklyReview(
            year=year,
            week_number=week_number,
            start_date=week_start,
            end_date=week_end,
        )

        # Track unique items for deduplication
        seen_tasks: list[tuple[str, Task]] = []  # (normalized_text, task)
        seen_people: dict[str, Person] = {}
        seen_decisions: list[tuple[str, Decision]] = []
        seen_meetings: list[tuple[str, Meeting]] = []
        seen_projects: dict[str, Project] = {}

        for content in contents:
            review.days_with_entries += 1

            # Aggregate tasks
            for task in content.tasks:
                if self._is_duplicate_task(task, seen_tasks):
                    continue
                seen_tasks.append((task.normalized_text, task))

                if task.status == TaskStatus.COMPLETED:
                    review.completed_tasks.append(task)
                else:
                    review.open_tasks.append(task)

            # Aggregate decisions
            for decision in content.decisions:
                if self._is_duplicate_decision(decision, seen_decisions):
                    continue
                seen_decisions.append((decision.text.lower(), decision))
                review.decisions.append(decision)

            # Aggregate people (merge mentions)
            for person in content.people:
                key = person.normalized_name
                if key in seen_people:
                    # Merge mentions
                    for mention in person.mentions:
                        seen_people[key].add_mention(
                            mention["context"],
                            mention["date"],
                            mention["source_file"]
                        )
                else:
                    seen_people[key] = person

            # Aggregate meetings
            for meeting in content.meetings:
                if self._is_duplicate_meeting(meeting, seen_meetings):
                    continue
                key = self._normalize_meeting(meeting)
                seen_meetings.append((key, meeting))
                review.meetings.append(meeting)

            # Aggregate projects
            for project in content.projects:
                key = project.name.lower().replace(" ", "")
                if key in seen_projects:
                    # Merge references
                    for ref in project.references:
                        seen_projects[key].add_reference(
                            ref["context"],
                            ref["date"],
                            ref["source_file"]
                        )
                    # Update task counts
                    seen_projects[key].tasks_count += project.tasks_count
                    seen_projects[key].completed_tasks_count += project.completed_tasks_count
                else:
                    seen_projects[key] = project

            # Collect topics
            for topic in content.topics:
                if topic not in review.topics:
                    review.topics.append(topic)

        # Finalize collections
        review.people = list(seen_people.values())
        review.projects = list(seen_projects.values())

        # Calculate project task counts from tasks
        self._update_project_stats(review)

        # Prioritize carry-overs
        self._prioritize_carry_overs(review)

        return review

    def _is_duplicate_task(self, task: Task, seen: list[tuple[str, Task]]) -> bool:
        """Check if a task is a duplicate using fuzzy matching."""
        if not seen:
            return False

        # Quick exact match
        for seen_norm, _ in seen:
            if task.normalized_text == seen_norm:
                return True

        # Fuzzy match if normalized text is long enough
        if len(task.normalized_text) < 10:
            return False

        seen_texts = [s[0] for s in seen]
        best_match = process.extractOne(
            task.normalized_text,
            seen_texts,
            scorer=fuzz.ratio,
            score_cutoff=self.fuzzy_threshold
        )

        if best_match:
            return True

        return False

    def _is_duplicate_decision(self, decision: Decision, seen: list[tuple[str, Decision]]) -> bool:
        """Check if a decision is a duplicate."""
        if not seen:
            return False

        text_lower = decision.text.lower()

        # Exact match
        for seen_text, _ in seen:
            if text_lower == seen_text:
                return True

        # Fuzzy match for longer decisions
        if len(text_lower) < 20:
            return False

        seen_texts = [s[0] for s in seen]
        best_match = process.extractOne(
            text_lower,
            seen_texts,
            scorer=fuzz.ratio,
            score_cutoff=self.fuzzy_threshold
        )

        return best_match is not None

    def _is_duplicate_meeting(self, meeting: Meeting, seen: list[tuple[str, Meeting]]) -> bool:
        """Check if a meeting is a duplicate."""
        if not seen:
            return False

        key = self._normalize_meeting(meeting)

        # Check for same day + similar title (e.g., same meeting recorded twice)
        for seen_key, seen_meeting in seen:
            if meeting.date == seen_meeting.date:
                # Same day, fuzzy title match
                score = fuzz.ratio(key, seen_key)
                if score >= self.fuzzy_threshold:
                    return True

        # Different days are NEVER duplicates (legitimate recurring meetings)
        # Only exception would be if start/end times are also identical
        return False

    def _normalize_meeting(self, meeting: Meeting) -> str:
        """Create a normalized key for meeting deduplication."""
        title = meeting.title.lower()
        # Remove links
        import re
        title = re.sub(r'\[\[([^\]]+)\]\]', r'\1', title)
        # Remove common words
        for word in ["call", "meeting", "sync", "with", "the", "a", "an"]:
            title = title.replace(f" {word} ", " ")
        # Compact
        return ' '.join(title.split())

    def _update_project_stats(self, review: WeeklyReview):
        """Update project statistics based on tasks."""
        project_map = {p.name.lower().replace(" ", ""): p for p in review.projects}

        for task in review.completed_tasks + review.open_tasks:
            # Find matching projects in task text
            for project in review.projects:
                if project.name.lower() in task.text.lower():
                    project.tasks_count += 1
                    if task.status == TaskStatus.COMPLETED:
                        project.completed_tasks_count += 1

    def _prioritize_carry_overs(self, review: WeeklyReview):
        """Prioritize open tasks for carry-over suggestions."""
        # Calculate age for each task
        today = date.today()

        for task in review.open_tasks:
            task.age_days = (today - task.source_date).days
            task.is_carry_over = task.age_days > 0

        # Sort by age (oldest first)
        sorted_tasks = sorted(
            review.open_tasks,
            key=lambda t: (t.age_days, t.source_file),
            reverse=True
        )

        # Categorize by priority
        high_threshold = self.config.carry_over_high_threshold
        medium_threshold = self.config.carry_over_medium_threshold

        for task in sorted_tasks:
            if task.age_days >= high_threshold:
                review.carry_overs_high.append(task)
            elif task.age_days >= medium_threshold:
                review.carry_overs_medium.append(task)
            else:
                review.carry_overs_recent.append(task)

        # Sort within categories by source date (oldest first)
        review.carry_overs_high.sort(key=lambda t: t.source_date)
        review.carry_overs_medium.sort(key=lambda t: t.source_date)
        review.carry_overs_recent.sort(key=lambda t: t.source_date)


def create_weekly_review(
    contents: list[ExtractedContent],
    week_start: date,
    week_end: date,
    year: int,
    week_number: int,
    config: Config,
    daily_notes_count: int = 0,
    work_contexts_count: int = 0
) -> WeeklyReview:
    """Create a weekly review from extracted content."""
    aggregator = FuzzyAggregator(config)
    review = aggregator.aggregate(contents, week_start, week_end, year, week_number)

    review.daily_notes_parsed = daily_notes_count
    review.work_contexts_parsed = work_contexts_count
    review.total_days = (week_end - week_start).days + 1

    return review
