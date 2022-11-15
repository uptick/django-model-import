import dataclasses
from typing import runtime_checkable, Protocol, Iterable

from django.forms import Field


@runtime_checkable
class HasSource(Protocol):
    """Matches any object that has a source property"""

    source: str | Iterable[str]


@dataclasses.dataclass
class ImportFieldMetadata:
    field: Field
    help_text: str = ""
    sources: list[tuple[str, ...]] = dataclasses.field(default_factory=list)
    required: bool = False
