import dataclasses
from typing import runtime_checkable, Protocol, Iterable

from django.forms import Field


@runtime_checkable
class HasSource(Protocol):
    """Matches any object that has a source property"""

    source: str | Iterable[str]


@dataclasses.dataclass
class ImportHeader:
    """Container for passing around header information"""

    field_name: str  # Name of the field on the form
    field: Field  # Instance of the form field
    name: str  # The name of the input header
    required: bool  # Weather the header is required on the form
    display: str = ""  # Verbose name of the header, Usually pulled from the model
    help_text: str = ""  # Help text of the header, pulled from the ImporterForm first, then the model
    alternatives: list[list["ImportHeader"]] = dataclasses.field(
        default_factory=list
    )  # A list of alternative headers the same field name
