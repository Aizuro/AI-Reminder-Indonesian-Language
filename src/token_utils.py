"""Utilitas token murni (tanpa torch) agar mudah diuji."""
from typing import List, Tuple

SPECIAL_TOKENS = {"[CLS]", "[SEP]", "[PAD]"}


def merge_subwords(tokens: List[str], labels: List[str]) -> Tuple[List[str], List[str]]:
    """
    Buang token spesial dan gabungkan sub-word WordPiece ('##') ke kata
    sebelumnya. Label kata = label sub-word pertamanya.

    ['se', '##teng', '##ah', '8'], ['B-TIME', 'I-TIME', 'I-TIME', 'I-TIME']
        -> ['setengah', '8'], ['B-TIME', 'I-TIME']
    """
    words: List[str] = []
    word_labels: List[str] = []
    for token, label in zip(tokens, labels):
        if token in SPECIAL_TOKENS:
            continue
        if token.startswith("##") and words:
            words[-1] += token[2:]
        else:
            words.append(token[2:] if token.startswith("##") else token)
            word_labels.append(label)
    return words, word_labels
