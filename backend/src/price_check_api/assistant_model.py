"""Load the trained intent model without making the API depend on artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"


@dataclass(frozen=True)
class AssistantModelState:
    pipeline: Any | None
    metadata: dict[str, Any]
    error: str | None = None


def load_assistant_model(model_dir: Path = MODEL_DIR) -> AssistantModelState:
    """Load only artifacts built with the installed scikit-learn version."""
    model_path = model_dir / "intent_pipeline.joblib"
    metadata_path = model_dir / "metadata.json"
    if not model_path.is_file() or not metadata_path.is_file():
        return AssistantModelState(
            None,
            {},
            "Trained assistant model is unavailable. Run `python scripts/train_assistant.py`.",
        )
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        import sklearn

        trained_version = metadata.get("sklearn_version")
        if trained_version != sklearn.__version__:
            return AssistantModelState(
                None,
                metadata,
                "Trained assistant model uses scikit-learn "
                f"{trained_version}; installed version is {sklearn.__version__}. "
                "Retrain it with `python scripts/train_assistant.py`.",
            )
        import joblib

        pipeline = joblib.load(model_path)
        return AssistantModelState(pipeline, metadata)
    except (ImportError, OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        return AssistantModelState(
            None,
            {},
            "Could not load trained assistant model: "
            f"{error}. Run `python scripts/train_assistant.py`.",
        )
