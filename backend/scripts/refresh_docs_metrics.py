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
FOLLOWUP_START = "<!-- followup:start -->"
FOLLOWUP_END = "<!-- followup:end -->"


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
    per_intent = {
        intent: values
        for intent, values in per_intent.items()
        if not (intent == "__abstain__" and values.get("support") == 0)
    }
    if not per_intent:
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
        + ", macro-F1 " + _value(synthetic.get("macro_f1"))
        + ", coverage " + _value(synthetic.get("coverage"))
        + ", abstained " + _value(synthetic.get("abstained")) + ".",
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
                f"{_value(result.get('accuracy'))}; macro-F1 {_value(result.get('macro_f1'))}; "
                f"coverage {_value(result.get('coverage'))}; "
                f"abstained {_value(result.get('abstained'))}.",
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


def render_followup_metrics(metadata: dict[str, Any], dialogues: dict[str, Any]) -> str:
    metrics = metadata.get("metrics", {}).get("synthetic_test", {})
    lines = [
        f"- Selected follow-up model: `{_value(metadata.get('model_name'))}`; "
        f"threshold {_value(metadata.get('confidence_threshold'))}.",
        f"- Synthetic follow-up test: rows {_value(metadata.get('synthetic_test_rows'))}; "
        f"accuracy {_value(metrics.get('accuracy'))}; macro-F1 {_value(metrics.get('macro_f1'))}.",
        "- Synthetic test precision / recall / F1 by label:",
        "| Label | Precision | Recall | F1 | Support |", "|---|---:|---:|---:|---:|",
    ]
    for label, values in sorted(metrics.get("per_label", {}).items()):
        lines.append(
            f"| {label} | {_value(values.get('precision'))} | {_value(values.get('recall'))} | "
            f"{_value(values.get('f1'))} | {_value(values.get('support'))} |"
        )
    for key, title in (("ai_written", "AI-written"), ("human_written", "Human-written")):
        result = dialogues.get(key)
        if result:
            lines.append(
                f"- {title} dialogues: turn accuracy {_value(result.get('turn_accuracy'))}; "
                f"dialogue success rate {_value(result.get('dialogue_success_rate'))}."
            )
    return "\n".join(lines)


def replace_section(path: Path, content: str) -> None:
    text = path.read_text(encoding="utf-8")
    start = text.index(START) + len(START)
    end = text.index(END, start)
    updated = text[:start] + "\n" + content + "\n" + text[end:]
    path.write_text(updated, encoding="utf-8")


def replace_optional_section(path: Path, start_marker: str, end_marker: str, content: str) -> None:
    text = path.read_text(encoding="utf-8")
    if start_marker not in text or end_marker not in text:
        return
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker, start)
    path.write_text(text[:start] + "\n" + content + "\n" + text[end:], encoding="utf-8")


def refresh(metadata_path: Path, docs_paths: tuple[Path, ...]) -> None:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    content = render_metrics(metadata)
    followup_path = metadata_path.with_name("followup_metadata.json")
    dialogue_path = metadata_path.with_name("dialogue_metrics.json")
    followup = (
        json.loads(followup_path.read_text(encoding="utf-8"))
        if followup_path.is_file()
        else {}
    )
    dialogues = (
        json.loads(dialogue_path.read_text(encoding="utf-8"))
        if dialogue_path.is_file()
        else {}
    )
    followup_content = (
        render_followup_metrics(followup, dialogues)
        if followup
        else "Follow-up classifier and dialogue evaluation metrics need refresh after training."
    )
    for path in docs_paths:
        replace_section(path, content)
        replace_optional_section(path, FOLLOWUP_START, FOLLOWUP_END, followup_content)


def main() -> int:
    metadata = json.loads(DEFAULT_METADATA.read_text(encoding="utf-8"))
    content = render_metrics(metadata)
    followup_path = ROOT / "backend/models/followup_metadata.json"
    followup = (
        json.loads(followup_path.read_text(encoding="utf-8"))
        if followup_path.is_file()
        else {}
    )
    dialogue_path = ROOT / "backend/models/dialogue_metrics.json"
    dialogues = (
        json.loads(dialogue_path.read_text(encoding="utf-8"))
        if dialogue_path.is_file()
        else {}
    )
    followup_content = render_followup_metrics(followup, dialogues) if followup else (
        "Follow-up classifier metrics need refresh after training."
    )
    for path in DEFAULT_DOCS:
        replace_section(path, content)
        replace_optional_section(path, FOLLOWUP_START, FOLLOWUP_END, followup_content)
        print(f"Refreshed metrics in {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
