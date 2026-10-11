import re


def normalize_word(word: str) -> str:
    return word.strip().casefold()


def censor(text: str, words) -> str:
    """Заменяет целые слова из words звёздочками (без учёта регистра)."""
    alt = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    if not alt:
        return text
    return re.sub(rf"(?<!\w)(?:{alt})(?!\w)", lambda m: "*" * len(m.group()), text, flags=re.I)

