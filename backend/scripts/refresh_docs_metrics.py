"""Refresh assistant metrics in the documentation from training metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METADATA = ROOT / "backend/models/metadata.json"
DEFAULT_DOCS = (ROOT / "docs/AI_REPORT.md", ROOT / "docs/MODEL_CARD.md")
START = "<!-- metrics:start -->"
END = "<!-- metrics:end -->"


def _value(value: Any, digits: int = 4) -> str:
    if value is None:
        return "not available"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _intent_table(metrics: dict[str, Any]) -> list[str]:
    per_intent = metrics.get("per_intent")
    if not isinstance(per_intent, dict) or not per_intent:
        return ["Per-intent precision/recall: not available"]
    lines = ["| Intent | Precision | Recall | F1 | Support |", "|---|---:|---:|---:|---:|"]
    for intent, values in sorted(per_intent.items()):
        lines.append(
            f"| {intent} | {_value(values.get('precision'))} | "
            f"{_value(values.get('recall'))} | {_value(values.get('f1'))} | "
            f"{_value(values.get('support'))} |"
        )
    return lines


def render_metrics(metadata: dict[str, Any]) -> str:
    metrics = metadata.get("metrics") or {}
    synthetic = metrics.get("synthetic_test") or {}
    heldout = metrics.get("heldout_by_source") or {}
    validation = metrics.get("validation") or {}
    leakage = metadata.get("leakage") or {}
    lines = [
        f"- Selected model: `{_value(metadata.get('model_name'))}`.",
        f"- Abstain threshold: {_value(metadata.get('confidence_threshold'))}; "
        f"validation coverage: {_value(validation.get('coverage'))}.",
        "- Rows: training " + _value(metadata.get("training_rows"))
        + ", validation " + _value(metadata.get("validation_rows"))
        + ", synthetic test " + _value(metadata.get("synthetic_test_rows")) + ".",
        "- Synthetic test: accuracy " + _value(synthetic.get("accuracy"))
        + ", macro-F1 " + _value(synthetic.get("macro_f1")) + ".",
        "- Synthetic test per-intent precision/recall:",
        *_intent_table(synthetic),
    ]
    heldout_titles = (
        ("ai_written", "AI-written held-out"),
        ("human_written", "Human-written held-out"),
    )
    for source, title in heldout_titles:
        if source == "human_written" and source not in heldout:
            continue
        result = heldout.get(source) or {}
        count = (metadata.get("heldout_rows_by_source") or {}).get(source)
        lines.extend(
            [
                f"- {title}: rows {_value(result.get('rows', count))}; accuracy "
                f"{_value(result.get('accuracy'))}; macro-F1 {_value(result.get('macro_f1'))}.",
                f"- {title} per-intent precision/recall:",
                *_intent_table(result),
            ]
        )
    if "ai_written" not in heldout:
        lines.extend(
            [
                "- AI-written held-out set: metrics not available.",
                "- AI-written held-out per-intent precision/recall: not available",
            ]
        )
    lines.extend(
        [
            "- Leakage check: training questions dropped at or above 0.85 similarity "
            f"{_value(leakage.get('training_rows_dropped_for_similarity'))}; highest retained "
            f"similarity {_value(leakage.get('highest_training_heldout_similarity'))} "
            f"({_value(leakage.get('closest_heldout_source'))}).",
            f"- Training date: {_value(metadata.get('training_date'))}.",
        ]
    )
    return "\n".join(lines)


def replace_section(path: Path, content: str) -> None:
    text = path.read_text(encoding="utf-8")
    start = text.index(START) + len(START)
    end = text.index(END, start)
    updated = text[:start] + "\n" + content + "\n" + text[end:]
    path.write_text(updated, encoding="utf-8")


def refresh(metadata_path: Path, docs_paths: tuple[Path, ...]) -> None:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    content = render_metrics(metadata)
    for path in docs_paths:
        replace_section(path, content)


def main() -> int:
    metadata = json.loads(DEFAULT_METADATA.read_text(encoding="utf-8"))
    content = render_metrics(metadata)
    for path in DEFAULT_DOCS:
        replace_section(path, content)
        print(f"Refreshed metrics in {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
