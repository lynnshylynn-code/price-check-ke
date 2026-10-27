import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from train_assistant import choose_threshold  # noqa: E402

from price_check_api.assistant_model import load_assistant_model  # noqa: E402


def test_validation_threshold_keeps_required_coverage():
    labels = ["cheapest_item", "out_of_scope", "cheapest_item", "out_of_scope"]
    classes = np.asarray(["cheapest_item", "out_of_scope"])
    probabilities = np.asarray(
        [[0.9, 0.1], [0.45, 0.55], [0.65, 0.35], [0.2, 0.8]],
    )
    threshold, metrics = choose_threshold(labels, classes, probabilities)
    assert 0 <= threshold <= 1
    assert metrics["coverage"] >= 0.70
    assert set(metrics) == {"macro_f1_with_abstentions", "accepted_accuracy", "coverage"}


def test_model_loader_reports_missing_artifacts_clearly(tmp_path):
    state = load_assistant_model(tmp_path)
    assert state.pipeline is None
    assert "model is unavailable" in state.error
    assert "train_assistant.py" in state.error
