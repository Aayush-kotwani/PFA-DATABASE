"""Export cell sanitization helper to neutralize spreadsheet formula injection."""

from typing import Any

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_export_cell(val: Any) -> Any:
    """Prefix dangerous leading formula characters with a single quote for string cells.

    Leaves numbers, booleans, dates, and None completely untouched.
    """
    if isinstance(val, str) and val and val[0] in FORMULA_PREFIXES:
        return f"'{val}"
    return val
