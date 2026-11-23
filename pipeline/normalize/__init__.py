import unicodedata


def label_key(text):
    """Search-only key. Never write this representation into upstream graphs."""
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())
