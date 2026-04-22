"""Writer for generating weekly review markdown output."""

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from jinja2 import Template, Environment, FileSystemLoader, PackageLoader

from weekly_review.models import WeeklyReview
from weekly_review.config import Config


# Default template as a string (used when no custom template specified)
DEFAULT_TEMPLATE = """# Weekly Review — {{ review.week_string }} ({{ review.date_range_string }})

## Week at a Glance
| Metric | Count |
|--------|-------|
| Days with entries | {{ review.days_with_entries }}/{{ review.total_days }} |
| Completed tasks | {{ review.completed_tasks|length }} |
| Unique people | {{ review.people|length }} |
| Meetings | {{ review.meetings|length }} |
| Decisions captured | {{ review.decisions|length }} |

{% if review.completed_tasks %}
## Completed This Week
{% for task in review.completed_tasks %}
- [x] {{ task.text }}{% if task.source_date %} ({{ task.source_date.strftime('%a %m/%d') }}){% endif %}
{%- endfor %}
{% else %}
## Completed This Week
_No completed tasks recorded this week._
{% endif %}

{% if review.decisions %}
## Key Decisions & Notes
{% for decision in review.decisions %}
- {{ decision.text }}{% if decision.source_date %} ({{ decision.source_date.strftime('%a') }}){% endif %}
{%- endfor %}
{% else %}
## Key Decisions & Notes
_No significant decisions recorded._
{% endif %}

{% if review.people %}
## People This Week
{% for person in review.people %}
- {% if person.page_link %}[[{{ person.page_link }}]]{% else %}{{ person.name }}{% endif %}{% if person.mentions %} — {{ person.mentions|length }} mention{{ 's' if person.mentions|length > 1 else '' }}{% endif %}
{%- endfor %}
{% else %}
## People This Week
_No people mentioned._
{% endif %}

{% if review.meetings %}
## Meetings & Time Blocks
{% for meeting in review.meetings %}
- {% if meeting.start_time and meeting.end_time %}{{ meeting.start_time }}-{{ meeting.end_time }} {% endif %}{{ meeting.title }}{% if meeting.attendees %} (with {% for p in meeting.attendees %}{% if not loop.first %}, {% endif %}[[{{ p }}]]{% endfor %}){% endif %}
{%- endfor %}
{% else %}
## Meetings & Time Blocks
_No meetings recorded._
{% endif %}

{% if review.projects %}
## Active Projects
{% for project in review.projects|sort(attribute='tasks_count', reverse=true) %}
- {% if project.page_link %}[[{{ project.page_link }}]]{% else %}{{ project.name }}{% endif %}{% if project.tasks_count %} — {{ project.completed_tasks_count }}/{{ project.tasks_count }} tasks{% endif %}
{%- endfor %}
{% else %}
## Active Projects
_No projects referenced._
{% endif %}

{% if review.topics %}
## Topics This Week
{% for topic in review.topics %}
- [[{{ topic }}]]
{%- endfor %}
{% endif %}

{% if review.carry_overs_high or review.carry_overs_medium or review.carry_overs_recent %}
## Carry-Over Suggestions (Prioritized)

{% if review.carry_overs_high %}
### 🔴 High Priority ({{ review.carry_overs_high|length }} items, 3+ days old)
{% for task in review.carry_overs_high %}
- [ ] {{ task.text }} (from {{ task.source_date.strftime('%a %m/%d') }})
{%- endfor %}
{% endif %}

{% if review.carry_overs_medium %}
### 🟡 Medium Priority ({{ review.carry_overs_medium|length }} items, 2 days old)
{% for task in review.carry_overs_medium %}
- [ ] {{ task.text }} (from {{ task.source_date.strftime('%a %m/%d') }})
{%- endfor %}
{% endif %}

{% if review.carry_overs_recent %}
### 🟢 Recent ({{ review.carry_overs_recent|length }} items, 1 day old)
{% for task in review.carry_overs_recent %}
- [ ] {{ task.text }}{% if task.is_carry_over %} (from {{ task.source_date.strftime('%a') }}){% endif %}
{%- endfor %}
{% endif %}
{% else %}
## Carry-Over Suggestions
_No open tasks to carry over. Great job!_ 🎉
{% endif %}

## Waiting-For Aging Check
_Review your waiting-for list and follow up on items older than expected._

---
*Generated: {{ review.generated_at.strftime('%Y-%m-%d %H:%M') }}*
*Source: {{ review.daily_notes_parsed }} daily notes + {{ review.work_contexts_parsed }} work-context files*

## Next Week Preview
- [ ] What are the 3 most important outcomes for next week?
- [ ] What meetings are already scheduled?
- [ ] What deadlines are approaching?
"""


class WeeklyReviewWriter:
    """Writer for generating weekly review markdown."""

    def __init__(self, config: Config):
        self.config = config
        self.env = Environment(
            loader=PackageLoader("weekly_review", "templates"),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, review: WeeklyReview) -> str:
        """Generate markdown for a weekly review."""
        # Try custom template first
        custom_template_path = self.config.get_template_path()

        if custom_template_path and custom_template_path.exists():
            template_content = custom_template_path.read_text(encoding="utf-8")
            template = Template(template_content)
        else:
            # Use default template
            template = Template(DEFAULT_TEMPLATE)

        return template.render(review=review, config=self.config)

    def write(
        self,
        review: WeeklyReview,
        output_path: Optional[Path] = None,
        dry_run: bool = False
    ) -> Optional[Path]:
        """Write the weekly review to file or stdout."""
        content = self.generate(review)

        if dry_run:
            print(content)
            return None

        # Determine output path
        if output_path is None:
            output_dir = self.config.get_output_dir()
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{review.week_string}.md"

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        output_path.write_text(content, encoding="utf-8")

        return output_path

    def get_default_output_path(self, review: WeeklyReview) -> Path:
        """Get the default output path for a review."""
        output_dir = self.config.get_output_dir()
        return output_dir / f"{review.week_string}.md"


def write_weekly_review(
    review: WeeklyReview,
    config: Config,
    output_path: Optional[Path] = None,
    dry_run: bool = False
) -> Optional[Path]:
    """Convenience function to write a weekly review."""
    writer = WeeklyReviewWriter(config)
    return writer.write(review, output_path, dry_run)


def generate_weekly_review_content(review: WeeklyReview, config: Config) -> str:
    """Generate weekly review content as string without writing."""
    writer = WeeklyReviewWriter(config)
    return writer.generate(review)
