"""Weekly Review Generator for Logseq knowledge graphs."""

__version__ = "0.1.0"
__author__ = "Thomas Bray"
__email__ = "thomas.bray@midtowntechgroup.com"

from weekly_review.config import Config, load_config
from weekly_review.models import (
    DailyNote,
    WorkContext,
    ExtractedContent,
    Task,
    Decision,
    Person,
    Meeting,
    Project,
    WeeklyReview,
)

__all__ = [
    "Config",
    "load_config",
    "DailyNote",
    "WorkContext",
    "ExtractedContent",
    "Task",
    "Decision",
    "Person",
    "Meeting",
    "Project",
    "WeeklyReview",
    "__version__",
]
