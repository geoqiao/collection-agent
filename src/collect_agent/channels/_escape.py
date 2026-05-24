"""XSS escaping utilities for channel output."""

from __future__ import annotations

import html


def escape_output(text: str) -> str:
    """Escape HTML special characters to prevent XSS.

    Escapes: &, <, >, ", '
    This should be applied at the system boundary before rendering
    content to any web-based UI or external system.
    """
    if not text:
        return text
    return html.escape(text, quote=True)
