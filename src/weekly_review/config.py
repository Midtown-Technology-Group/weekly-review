"""Configuration management for weekly review."""

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Weekly review configuration."""
    # Paths (relative to knowledge graph root)
    knowledge_graph_root: Path = field(default_factory=lambda: Path("."))
    daily_notes_path: Path = field(default_factory=lambda: Path("daily"))
    work_context_path: Path = field(default_factory=lambda: Path("pages"))
    output_path: Path = field(default_factory=lambda: Path("reviews/weekly"))

    # Fuzzy matching threshold (0-100)
    fuzzy_threshold: int = 85

    # Date format for parsing
    date_format: str = "%Y-%m-%d"

    # Sections to include in output
    sections: list[str] = field(default_factory=lambda: [
        "metrics",
        "completed",
        "decisions",
        "people",
        "meetings",
        "projects",
        "carryovers",
        "waiting_for",
    ])

    # Template settings
    template: str = "default"  # or path to custom jinja2 template

    # Carry-over priority thresholds (days)
    carry_over_high_threshold: int = 3
    carry_over_medium_threshold: int = 2

    # Task patterns to exclude (regex)
    excluded_task_patterns: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> "Config":
        """Load config from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data, path.parent)

    @classmethod
    def from_dict(cls, data: dict, root_path: Path = Path(".")) -> "Config":
        """Create config from dictionary."""
        config = cls(knowledge_graph_root=root_path)

        if "daily_notes_path" in data:
            config.daily_notes_path = Path(data["daily_notes_path"])
        if "work_context_path" in data:
            config.work_context_path = Path(data["work_context_path"])
        if "output_path" in data:
            config.output_path = Path(data["output_path"])
        if "fuzzy_threshold" in data:
            config.fuzzy_threshold = data["fuzzy_threshold"]
        if "date_format" in data:
            config.date_format = data["date_format"]
        if "sections" in data:
            config.sections = data["sections"]
        if "template" in data:
            config.template = data["template"]
        if "carry_over_high_threshold" in data:
            config.carry_over_high_threshold = data["carry_over_high_threshold"]
        if "carry_over_medium_threshold" in data:
            config.carry_over_medium_threshold = data["carry_over_medium_threshold"]
        if "excluded_task_patterns" in data:
            config.excluded_task_patterns = data["excluded_task_patterns"]

        return config

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            "daily_notes_path": str(self.daily_notes_path),
            "work_context_path": str(self.work_context_path),
            "output_path": str(self.output_path),
            "fuzzy_threshold": self.fuzzy_threshold,
            "date_format": self.date_format,
            "sections": self.sections,
            "template": self.template,
            "carry_over_high_threshold": self.carry_over_high_threshold,
            "carry_over_medium_threshold": self.carry_over_medium_threshold,
            "excluded_task_patterns": self.excluded_task_patterns,
        }

    def get_daily_notes_dir(self) -> Path:
        """Get absolute path to daily notes directory."""
        return self.knowledge_graph_root / self.daily_notes_path

    def get_work_context_dir(self) -> Path:
        """Get absolute path to work context directory."""
        return self.knowledge_graph_root / self.work_context_path

    def get_output_dir(self) -> Path:
        """Get absolute path to output directory."""
        return self.knowledge_graph_root / self.output_path

    def get_template_path(self) -> Optional[Path]:
        """Get path to custom template, or None if using default."""
        if self.template == "default":
            return None
        path = Path(self.template)
        if path.is_absolute():
            return path
        return self.knowledge_graph_root / path


def find_config_file(start_path: Path = Path(".")) -> Optional[Path]:
    """Find config file by walking up directories."""
    config_names = ["weekly-review.yaml", "weekly-review.yml", ".weekly-review.yaml"]

    current = start_path.resolve()
    while True:
        for name in config_names:
            config_path = current / name
            if config_path.exists():
                return config_path

        # Stop at root
        if current.parent == current:
            break
        current = current.parent

    return None


def load_config(start_path: Path = Path(".")) -> Config:
    """Load configuration from file or return defaults."""
    config_path = find_config_file(start_path)

    if config_path:
        return Config.from_yaml(config_path)

    # Return defaults with current directory as root
    return Config(knowledge_graph_root=start_path.resolve())


def init_config(path: Path) -> Path:
    """Initialize a new config file at the specified path."""
    config = Config(knowledge_graph_root=path.parent)

    config_path = path
    if path.is_dir():
        config_path = path / "weekly-review.yaml"

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)

    return config_path
