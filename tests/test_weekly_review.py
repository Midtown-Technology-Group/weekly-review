"""Tests for weekly review generator."""

from datetime import date
from pathlib import Path

import pytest

from weekly_review.models import Task, TaskStatus, Person, Decision, Meeting, Project
from weekly_review.aggregator import FuzzyAggregator
from weekly_review.config import Config


class TestTaskNormalization:
    """Test task text normalization for fuzzy matching."""

    def test_normalize_removes_brackets(self):
        task = Task(
            text="Review [[Bifrost]] documentation",
            status=TaskStatus.OPEN,
            source_file="test.md",
            source_date=date(2026, 4, 15)
        )
        assert "bifrost" in task.normalized_text
        assert "[[" not in task.normalized_text

    def test_normalize_removes_ticket_numbers(self):
        task = Task(
            text="Fix T20260127.0054 power issues",
            status=TaskStatus.OPEN,
            source_file="test.md",
            source_date=date(2026, 4, 15)
        )
        assert "t20260127.0054" not in task.normalized_text
        assert "fix" in task.normalized_text
        assert "power issues" in task.normalized_text

    def test_normalize_lowercases(self):
        task = Task(
            text="URGENT: Review CIPP Deployments",
            status=TaskStatus.OPEN,
            source_file="test.md",
            source_date=date(2026, 4, 15)
        )
        assert task.normalized_text == "urgent: review cipp deployments"


class TestFuzzyAggregator:
    """Test fuzzy deduplication logic."""

    @pytest.fixture
    def config(self):
        return Config(
            knowledge_graph_root=Path("."),
            fuzzy_threshold=85
        )

    @pytest.fixture
    def aggregator(self, config):
        return FuzzyAggregator(config)

    def test_duplicate_tasks_detected(self, aggregator):
        task1 = Task(
            text="Review CIPP deployment configuration",
            status=TaskStatus.COMPLETED,
            source_file="day1.md",
            source_date=date(2026, 4, 15)
        )
        task2 = Task(
            text="Review CIPP deployment config",
            status=TaskStatus.COMPLETED,
            source_file="day2.md",
            source_date=date(2026, 4, 16)
        )

        seen = [(task1.normalized_text, task1)]
        is_dup = aggregator._is_duplicate_task(task2, seen)
        # These should be similar enough to be considered duplicates
        assert is_dup

    def test_different_tasks_not_detected(self, aggregator):
        task1 = Task(
            text="Review CIPP deployment",
            status=TaskStatus.COMPLETED,
            source_file="day1.md",
            source_date=date(2026, 4, 15)
        )
        task2 = Task(
            text="Fix Halo ticket import",
            status=TaskStatus.COMPLETED,
            source_file="day2.md",
            source_date=date(2026, 4, 16)
        )

        seen = [(task1.normalized_text, task1)]
        is_dup = aggregator._is_duplicate_task(task2, seen)
        assert not is_dup


class TestPersonExtraction:
    """Test person name extraction and normalization."""

    def test_person_normalized_name(self):
        person = Person(name="Steven Keath")
        assert person.normalized_name == "stevenkeath"

    def test_person_add_mention(self):
        person = Person(name="Mike")
        person.add_mention("Call with Mike about migration", date(2026, 4, 15), "test.md")
        assert len(person.mentions) == 1
        assert person.mentions[0]["context"] == "Call with Mike about migration"


class TestDecisionExtraction:
    """Test decision content detection."""

    def test_decision_creation(self):
        decision = Decision(
            text="Implemented CIPP automatic deployments",
            source_file="test.md",
            source_date=date(2026, 4, 15),
            projects=["cipp"]
        )
        assert decision.text == "Implemented CIPP automatic deployments"
        assert "cipp" in decision.projects


class TestConfig:
    """Test configuration loading."""

    def test_default_config(self):
        config = Config()
        assert config.fuzzy_threshold == 85
        assert config.daily_notes_path == Path("daily")
        assert config.work_context_path == Path("pages")

    def test_config_paths(self, tmp_path):
        config = Config(knowledge_graph_root=tmp_path)
        assert config.get_daily_notes_dir() == tmp_path / "daily"
        assert config.get_work_context_dir() == tmp_path / "pages"


class TestDateUtils:
    """Test date utility functions."""

    def test_iso_week_dates(self):
        from weekly_review.cli import get_iso_week_dates
        start, end = get_iso_week_dates(2026, 16)

        # ISO week 16, 2026 should start on Monday
        assert start.weekday() == 0  # Monday
        assert end.weekday() == 6    # Sunday

        # Check dates
        assert start.year == 2026
        assert end.year == 2026

        # Should span 7 days
        assert (end - start).days == 6

    def test_parse_week_string(self):
        from weekly_review.cli import parse_week_string
        year, week = parse_week_string("2026-W16")
        assert year == 2026
        assert week == 16


class TestMeetingNormalization:
    """Test meeting deduplication."""

    @pytest.fixture
    def config(self):
        return Config(fuzzy_threshold=85)

    @pytest.fixture
    def aggregator(self, config):
        return FuzzyAggregator(config)

    def test_normalize_meeting(self, aggregator):
        meeting = Meeting(
            title="Call with [[Mike]] about migration",
            date=date(2026, 4, 15),
            attendees=["Mike"]
        )
        key = aggregator._normalize_meeting(meeting)
        assert "mike" in key
        assert "[[" not in key

    def test_same_day_same_meeting_detected(self, aggregator):
        # Very similar meetings on same day should be detected as duplicates
        meeting1 = Meeting(
            title="Call with Mike about Brothers project",
            date=date(2026, 4, 15),
            start_time="09:30"
        )
        meeting2 = Meeting(
            title="call with Mike about Brothers project update",
            date=date(2026, 4, 15),
            start_time="09:37"
        )

        seen = [(aggregator._normalize_meeting(meeting1), meeting1)]
        is_dup = aggregator._is_duplicate_meeting(meeting2, seen)
        # Same day, very similar content should be detected as duplicate
        assert is_dup

    def test_different_days_not_duplicate(self, aggregator):
        # Same meeting on different days are NOT duplicates (legitimate repeats)
        meeting1 = Meeting(
            title="Daily standup with team",
            date=date(2026, 4, 15)
        )
        meeting2 = Meeting(
            title="Daily standup with team",
            date=date(2026, 4, 16)
        )

        seen = [(aggregator._normalize_meeting(meeting1), meeting1)]
        is_dup = aggregator._is_duplicate_meeting(meeting2, seen)
        # Different days should not be considered duplicates even with same title
        assert not is_dup

    def test_same_day_different_meetings_not_duplicate(self, aggregator):
        # Different meetings on same day should not be marked as duplicates
        meeting1 = Meeting(
            title="Call with Mike about Brothers Excavating",
            date=date(2026, 4, 15),
            start_time="09:30"
        )
        meeting2 = Meeting(
            title="call with Mike about migration strategy",
            date=date(2026, 4, 15),
            start_time="14:00"
        )

        seen = [(aggregator._normalize_meeting(meeting1), meeting1)]
        is_dup = aggregator._is_duplicate_meeting(meeting2, seen)
        # Different topics should not be considered duplicates
        assert not is_dup


class TestProjectStats:
    """Test project statistics aggregation."""

    def test_project_task_counts(self):
        from weekly_review.models import WeeklyReview

        review = WeeklyReview(
            year=2026,
            week_number=16,
            start_date=date(2026, 4, 14),
            end_date=date(2026, 4, 20)
        )

        project = Project(name="cipp", page_link="projects/cipp")
        project.tasks_count = 5
        project.completed_tasks_count = 3

        review.projects = [project]

        assert project.tasks_count == 5
        assert project.completed_tasks_count == 3
