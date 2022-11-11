import dataclasses
from typing import runtime_checkable, Protocol, Iterable

from django.forms import Field


@runtime_checkable
class HasSource(Protocol):
    source: str | Iterable[str]


@dataclasses.dataclass
class ImportHeader:
    field_name: str
    field: Field
    name: str
    required: bool
    display: str = ""
    help_text: str = ""
    alternatives: list[list["ImportHeader"]] = dataclasses.field(default_factory=list)
