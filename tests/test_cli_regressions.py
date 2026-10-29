"""CLI regressions using disposable synthetic knowledge graphs."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from weekly_review.cli import app


@pytest.mark.parametrize("dry_run", [True, False])
def test_generate_uses_exact_config_file(tmp_path: Path, monkeypatch, dry_run: bool):
    """An explicit nonstandard filename must win over auto-discovery."""
    graph = tmp_path / "graph"
    graph.mkdir()
    (graph / "weekly-review.yaml").write_text("output_path: wrong-output\n", encoding="utf-8")
    (graph / "selected.yaml").write_text(
        "daily_notes_path: selected-daily\noutput_path: selected-output\n", encoding="utf-8"
    )
    daily = graph / "selected-daily"
    daily.mkdir()
    (daily / "2026-04-15.md").write_text(
        "# Next Actions\n- [ ] Inspect synthetic widget\n", encoding="utf-8"
    )
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    args = ["generate", "2026-W16", "--config", str(graph / "selected.yaml")]
    if dry_run:
        args.append("--dry-run")
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    if dry_run:
        assert "Inspect synthetic widget" in result.output
        assert not (graph / "selected-output").exists()
    else:
        output = graph / "selected-output" / "2026-W16.md"
        assert output.exists(), result.output
        assert "Inspect synthetic widget" in output.read_text(encoding="utf-8")
    assert not (graph / "wrong-output").exists()
    assert not (elsewhere / "reviews").exists()


@pytest.mark.parametrize("week", [None, "2026-W16"])
def test_preview_is_a_working_no_write_alias(tmp_path: Path, monkeypatch, week):
    """Preview must receive CLI defaults rather than Typer OptionInfo objects."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "weekly-review.yaml").write_text("output_path: reviews\n", encoding="utf-8")
    args = ["preview"] + ([week] if week else [])
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, repr(result.exception)
    assert "# Weekly Review" in result.output
    assert "Preview (dry run)" in result.output
    if week:
        assert week in result.output
    assert not (tmp_path / "reviews").exists()
