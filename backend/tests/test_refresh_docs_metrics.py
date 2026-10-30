import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from refresh_docs_metrics import refresh, render_metrics  # noqa: E402


def test_refresh_fills_markers_and_preserves_surrounding_text(tmp_path: Path) -> None:
    metadata = {
        "model_name": "UnitTestModel",
        "training_date": "2026-10-30",
        "training_rows": 12,
        "validation_rows": 4,
        "synthetic_test_rows": 5,
        "confidence_threshold": 0.6,
        "validation": {"coverage": 0.9},
        "metrics": {
            "validation": {"coverage": 0.9},
            "synthetic_test": {
                "accuracy": 0.8,
                "macro_f1": 0.7,
                "per_intent": {
                    "cheapest_item": {
                        "precision": 0.75,
                        "recall": 0.5,
                        "f1": 0.6,
                        "support": 2,
                    }
                },
            },
            "heldout_by_source": {
                "ai_written": {"rows": 3, "accuracy": 1.0, "macro_f1": 0.9}
            },
        },
        "leakage": {
            "training_rows_dropped_for_similarity": 1,
            "highest_training_heldout_similarity": 0.84,
            "closest_heldout_source": "AI-written held-out",
        },
        "heldout_rows_by_source": {"ai_written": 3},
    }
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    docs = tmp_path / "report.md"
    docs.write_text(
        "before\n<!-- metrics:start -->\nold\n<!-- metrics:end -->\nafter\n",
        encoding="utf-8",
    )

    refresh(metadata_path, (docs,))
    rendered_once = docs.read_text(encoding="utf-8")
    refresh(metadata_path, (docs,))

    assert docs.read_text(encoding="utf-8") == rendered_once
    assert rendered_once.startswith("before\n<!-- metrics:start -->")
    assert rendered_once.endswith("<!-- metrics:end -->\nafter\n")
    assert "UnitTestModel" in rendered_once
    assert "| cheapest_item | 0.7500 | 0.5000 | 0.6000 | 2 |" in rendered_once


def test_metrics_renderer_marks_missing_metadata_as_unavailable() -> None:
    rendered = render_metrics({"metrics": {}})

    assert "Selected model: `not available`" in rendered
    assert "not available" in rendered
    assert "AI-written held-out set: metrics not available" in rendered
