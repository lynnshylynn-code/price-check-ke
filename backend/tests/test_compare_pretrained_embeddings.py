import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compare_pretrained_embeddings  # noqa: E402


def test_optional_embedding_comparison_exits_cleanly_without_dependency(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        compare_pretrained_embeddings.importlib.util,
        "find_spec",
        lambda _name: None,
    )

    assert compare_pretrained_embeddings.main([]) == 0
    assert "not installed" in capsys.readouterr().out
