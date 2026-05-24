"""Safe XML parsing utilities with entity expansion protection."""

from __future__ import annotations

import xml.etree.ElementTree as ET

MAX_XML_SIZE = 100_000  # 100KB max XML payload


def safe_xml_fromstring(xml_text: str) -> ET.Element:
    """Parse XML safely with size limit and no entity expansion.

    Raises ValueError if XML is too large or contains entities.
    """
    if len(xml_text) > MAX_XML_SIZE:
        raise ValueError(
            f"XML payload too large: {len(xml_text)} bytes > {MAX_XML_SIZE}"
        )

    # Reject XML with DOCTYPE declarations (entities)
    upper = xml_text.upper()
    if "<!DOCTYPE" in upper or "<!ENTITY" in upper:
        raise ValueError("XML entities are not allowed")

    return ET.fromstring(xml_text)
