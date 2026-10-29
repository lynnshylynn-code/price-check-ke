from price_check_api.listing_groups import _match_score


def test_match_score_combines_word_overlap_and_tfidf_for_noisy_variants():
    assert _match_score("Brookside UHT Milk 500ml", "Milk 500 ml Brookside UHT") > 0.8
    assert _match_score("Brookside Milk 500ml", "Samsung 55 inch TV") < 0.2
