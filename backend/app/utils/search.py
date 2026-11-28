"""Search query sanitization helpers."""


def escape_like(term: str, escape_char: str = "\\") -> str:
    """Escape SQL LIKE/ILIKE wildcard characters (%, _) and the escape character."""
    return (
        term.replace(escape_char, escape_char + escape_char)
        .replace("%", f"{escape_char}%")
        .replace("_", f"{escape_char}_")
    )
