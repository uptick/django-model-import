from functools import cached_property
from typing import TypeVar, TYPE_CHECKING

from django.db.models.fields import NOT_PROVIDED
from django.forms import modelform_factory

from .fields import JSONField, FlatRelatedField

if TYPE_CHECKING:
    from . import ImporterModelForm  # NOQA

_ImporterForm = TypeVar("_ImporterForm", bound="ImporterModelForm")


class FormClassBuilder:
    """Constructs instances of ImporterModelForm, taking headers into account."""

    def __init__(self, modelimportformclass: _ImporterForm, headers: list[str]) -> None:
        self.headers = headers
        self.modelimportformclass = modelimportformclass
        self.model = modelimportformclass.Meta.model

    def build_update_form(self) -> _ImporterForm:
        return self._get_modelimport_form_class(fields=self.valid_fields)

    def build_create_form(self) -> _ImporterForm:
        # Combine valid & required fields; preserving order of valid fields.
        form_fields = self.valid_fields + list(
            set(self.required_fields) - set(self.valid_fields)
        )
        return self._get_modelimport_form_class(fields=form_fields)

    @cached_property
    def valid_fields(self) -> list[str]:
        """Using the provided headers, prepare a list of valid
        fields for this importer. Preserves field ordering as defined by the headers.
        """

        # Get the viable headers for the importer class
        form_field_metadata = self.modelimportformclass.get_field_metadata()

        # Check each header combination against the input headers to
        # see if they evaluate to a field
        valid_present_fields = set()
        for field_name, field_meta in form_field_metadata.items():
            if isinstance(field_meta.field, (FlatRelatedField, JSONField)):
                # FlatRelatedField: these are a collection of other columns that build a relation on the fly. Always add.
                # JSONField: these are provided as FIELDNAME__SOME_DATA, so won't match directly. Just let the whole thing through.
                valid_present_fields.add(field_name)
            else:
                for source in field_meta.sources:
                    if {key for key, _ in source} <= set(self.headers):
                        valid_present_fields.add(field_name)

        return list(valid_present_fields)

    @cached_property
    def required_fields(self) -> list[str]:
        fields = self.model._meta.get_fields()
        required_fields = []

        # Required means `blank` is False and `editable` is True.
        for f in fields:
            # Note - if the field doesn't have a `blank` attribute it is probably
            # a ManyToOne relation (reverse foreign key), which you probably want to ignore.
            if (
                getattr(f, "blank", True) is False
                and getattr(f, "editable", True) is True
                and f.default is NOT_PROVIDED
            ):
                required_fields.append(f.name)
        return required_fields

    def _get_modelimport_form_class(self, fields) -> _ImporterForm:
        """Return a modelform for use with this data.

        We use a modelform_factory to dynamically limit the fields on the import,
        otherwise the absence of a value can be taken as false for boolean fields,
        where as we want the model's default value to kick in.
        """
        klass = modelform_factory(
            self.model,
            form=self.modelimportformclass,
            fields=fields,
        )
        # Remove fields altogether if they haven't been specified in the import (makes sense for updates). #houseofcards..
        base_fields_to_del = set(klass.base_fields.keys()) - set(fields)
        for f in base_fields_to_del:
            del klass.base_fields[f]
        return klass
