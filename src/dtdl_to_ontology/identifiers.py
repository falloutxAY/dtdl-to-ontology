"""Role-aware DTDL v3 identifiers, distinct from generated system identifiers."""

import re

_SEGMENT = r"[A-Za-z](?:[A-Za-z0-9_]*[A-Za-z0-9])?"
_VERSION = r"(?:;[1-9][0-9]{0,8}(?:\.[1-9][0-9]{0,5})?)?"
DTMI = re.compile(rf"dtmi:{_SEGMENT}(?::{_SEGMENT})*{_VERSION}\Z")
SYSTEM_DTMI = re.compile(
    rf"dtmi:(?:{_SEGMENT}|_[A-Za-z0-9_]*[A-Za-z0-9])"
    rf"(?::(?:{_SEGMENT}|_[A-Za-z0-9_]*[A-Za-z0-9]))*{_VERSION}\Z"
)


def valid_dtmi(value: object, role: str = "reference") -> bool:
    if not isinstance(value, str):
        return False
    limit = 128 if role == "interface" else 4096 if role == "generated" else 2048
    pattern = SYSTEM_DTMI if role == "generated" else DTMI
    return (
        len(value) <= limit
        and pattern.fullmatch(value) is not None
        and (
            role not in {"interface", "element"}
            or not value.startswith(("dtmi:dtdl:", "dtmi:standard:"))
        )
    )


def automatic_id(parent: str, member: str, name: str | None = None) -> str:
    body, separator, version = parent.partition(";")
    suffix = f":_{member}" + (f":__{name}" if name else "")
    return body + suffix + (separator + version if separator else "")
