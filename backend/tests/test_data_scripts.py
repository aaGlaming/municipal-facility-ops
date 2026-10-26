from pathlib import Path

from scripts.backup_data import copy_tree_with_manifest
from scripts.generate_synthetic_data import generate_synthetic_data
from scripts.prepare_data import prepare_events


def test_synthetic_generation_marks_source_and_is_repeatable(tmp_path: Path) -> None:
    first = generate_synthetic_data(tmp_path / "first", seed=7, facility_count=3)
    second = generate_synthetic_data(tmp_path / "second", seed=7, facility_count=3)
    assert first["synthetic_facilities.csv"] == second["synthetic_facilities.csv"]
    assert "source_type" in first["synthetic_facilities.csv"]


def test_prepare_events_writes_unified_output(tmp_path: Path) -> None:
    raw = tmp_path / "raw.csv"
    raw.write_text("unique_key,category,status\nA,Street Light Condition,Open\n", encoding="utf-8")
    output = tmp_path / "processed.csv"
    result = prepare_events([raw], output)
    assert result["rows"] == 1
    assert output.read_text(encoding="utf-8").splitlines()[0].startswith("event_id,")


def test_backup_records_hashes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    (source / "a.txt").write_text("hello", encoding="utf-8")
    report = copy_tree_with_manifest(source, target)
    assert report["copied_files"] == 1
    assert report["mismatches"] == []
