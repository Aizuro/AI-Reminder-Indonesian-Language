from src.token_utils import merge_subwords


def test_merges_subwords_and_drops_special_tokens():
    toks = ["[CLS]", "se", "##teng", "##ah", "8", "pagi", "[SEP]", "[PAD]"]
    labs = ["O", "B-TIME", "I-TIME", "I-TIME", "I-TIME", "I-TIME", "O", "O"]
    words, wl = merge_subwords(toks, labs)
    assert words == ["setengah", "8", "pagi"]
    assert wl == ["B-TIME", "I-TIME", "I-TIME"]


def test_no_subwords_is_identity():
    words, wl = merge_subwords(["besok", "jam", "7"], ["B-DATE", "B-TIME", "I-TIME"])
    assert words == ["besok", "jam", "7"] and wl == ["B-DATE", "B-TIME", "I-TIME"]


def test_leading_subword_without_predecessor_is_kept():
    words, wl = merge_subwords(["##ah", "x"], ["O", "O"])
    assert words == ["ah", "x"] and wl == ["O", "O"]
