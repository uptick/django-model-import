import dataclasses
from typing import runtime_checkable, Protocol, Iterable

from django.forms import Field


@runtime_checkable
class HasSource(Protocol):
    """Matches any object that has a source property"""

    source: str | Iterable[str]


@dataclasses.dataclass
class ImportFieldMetadata:
    """Describes how a field maps to headers during an import

    For `sources`, they are defined as a list of a group of headers that satisfy the field.
    """

    field: Field
    help_text: str = ""
    sources: list[list[tuple[str, str]]] = dataclasses.field(default_factory=list)
    required: bool = False
