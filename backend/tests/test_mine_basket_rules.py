import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mine_basket_rules import generate_synthetic_transactions, write_synthetic_transactions  # noqa: E402

from price_check_api.association_rules import read_transactions  # noqa: E402


def test_synthetic_basket_generator_is_seeded_and_marks_provenance(tmp_path: Path) -> None:
    assert generate_synthetic_transactions(8, seed=7) == generate_synthetic_transactions(
        8, seed=7
    )
    output = tmp_path / "synthetic.csv"

    write_synthetic_transactions(output, count=8, seed=7)

    transactions = read_transactions(str(output))
    assert len(transactions) == 8
    assert any({"bread", "milk-1l"}.issubset(row) for row in transactions)
    assert any({"maize-meal-2kg", "cooking-oil-1l"}.issubset(row) for row in transactions)
