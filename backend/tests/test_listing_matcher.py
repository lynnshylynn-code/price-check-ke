from types import SimpleNamespace

from sklearn.feature_extraction.text import TfidfVectorizer

from price_check_api.listing_matcher import pair_features


def test_pair_features_cover_names_size_brand_and_unit_price() -> None:
    left = SimpleNamespace(
        item_name="Golden Butter Cookies 200G",
        pack_size="200G",
        unit="g",
        unit_price=0.5,
    )
    right = SimpleNamespace(
        item_name="Golden Butter Cookies 400G",
        pack_size="400G",
        unit="g",
        unit_price=0.4,
    )
    names = [left.item_name, right.item_name]
    word = TfidfVectorizer(ngram_range=(1, 2)).fit(names)
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4)).fit(names)
    features = pair_features(left, right, word, char)
    assert len(features) == 9
    assert features[0] > 0
    assert features[3] == 0.0
    assert features[4] == 1.0
    assert features[5] == 1.0
