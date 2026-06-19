import operator
from collections.abc import Collection, Hashable, Iterable, Mapping
from typing import Any

from django import forms
from django.forms.renderers import BaseRenderer
from django.utils.safestring import SafeText

type Choices[Key: Hashable, Value: Hashable] = Collection[tuple[Key, Value]]


class DisplayChoiceWidget[Key: Hashable, Value: Hashable](forms.Widget):
    """This widget is helpful when the value being uploaded by the customer is the
    display choice, not the value. This widget will map the display choice back to the value.
    """

    @staticmethod
    def flip_enum(choices: Choices[Key, Value]) -> dict[Value, Key]:
        return dict(zip(dict(choices).values(), dict(choices).keys(), strict=False))

    def __init__(self, choices: Choices[Key, Value], *args: Any, **kwargs: Any) -> None:
        self.choices: Choices[Key, Value] = choices
        self.display_to_choice_map: dict[Value, Key] = self.flip_enum(choices)
        super().__init__(*args, **kwargs)

    def value_from_datadict(
        self, data: dict[str, Any], files: Mapping[str, Iterable[Any]], name: str
    ) -> Key | None:
        """
        Given a dictionary of data and this widget's name, return the value
        of this widget or None if it's not provided.
        """
        val = data.get(name)
        return self.display_to_choice_map.get(val) if val is not None else None

    def format_value(self, value: Any) -> str | None:
        return str(result) if (result := dict(self.choices).get(value)) else None


class CompositeLookupWidget(forms.Widget):
    def __init__(self, source: Collection[str], *args: Any, **kwargs: Any) -> None:
        self.source: Collection[str] = source
        super().__init__(*args, **kwargs)

    def value_from_datadict(
        self, data: dict[str, Any], files: Mapping[str, Iterable[Any]], name: str
    ) -> Any | None:
        getter = operator.itemgetter(*self.source)
        try:
            return getter(data)
        except KeyError:
            pass

    def value_omitted_from_data(
        self, data: dict[str, Any], files: Mapping[str, Iterable[Any]], name: str
    ) -> bool:
        for field_name in self.source:
            if field_name not in data:
                return True
        return False


class NamedSourceWidget(forms.Widget):
    """This lets you override the column from which to import data."""

    def __init__(self, source: str, *args: Any, **kwargs: Any) -> None:
        self.source: str = source
        super().__init__(*args, **kwargs)

    def value_from_datadict(
        self, data: dict[str, Any], files: Mapping[str, Iterable[Any]], name: str
    ) -> Any:
        return data.get(self.source, "")

    def value_omitted_from_data(
        self, data: dict[str, Any], files: Mapping[str, Iterable[Any]], name: str
    ) -> bool:
        return self.source not in data


class JSONFieldWidget(forms.Widget):
    template_name = "django/forms/widgets/textarea.html"

    def render(
        self,
        name: str,
        value: Any,
        attrs: dict[str, Any] | None = None,
        renderer: BaseRenderer | None = None,
    ) -> SafeText:
        return SafeText("")

    def value_omitted_from_data(
        self, data: dict[str, Any], files: Mapping[str, Iterable[Any]], name: str
    ) -> bool:
        return not any([key.startswith(name) for key in data.keys()])

    def value_from_datadict(
        self, data: dict[str, Any], files: Mapping[str, Iterable[Any]], name: str
    ) -> dict[str, Any]:
        extra_fields = {}
        for f in data.keys():
            if f.startswith(name):
                new_field = f[len(name) + 1 :]
                extra_fields[new_field] = data[f]
        return extra_fields
