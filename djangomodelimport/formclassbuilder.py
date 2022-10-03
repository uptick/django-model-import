from functools import cached_property

from django.db.models.fields import NOT_PROVIDED
from django.forms import modelform_factory

from djangomodelimport.widgets import NamedSourceWidget, CompositeLookupWidget

from .fields import FlatRelatedField, JSONField, SourceFieldSwitcher

class FormClassBuilder:
    """Constructs instances of ImporterModelForm, taking headers into account."""
    def __init__(self, modelimportformclass, headers):
        self.headers = headers
        self.modelimportformclass = modelimportformclass
        self.model = modelimportformclass.Meta.model

    def build_update_form(self):
        return self._get_modelimport_form_class(fields=self.valid_fields)

    def build_create_form(self):
        # Combine valid & required fields; preserving order of valid fields.
        form_fields = self.valid_fields + list(set(self.required_fields) - set(self.valid_fields))
        return self._get_modelimport_form_class(fields=form_fields)

    @cached_property
    def valid_fields(self):
        """ Using the provided headers, prepare a list of valid fields for this importer.
            Preservers field ordering as defined by the headers.
        """
        # 1) Determine which of the provided import headers are legitimate by comparing directly against the form fields.
        valid_present_fields = [field for field in self.headers if field in self.modelimportformclass.base_fields]
        # 2) Add virtual fields:
        # - FlatRelatedField: these are a collection of other columns that build a relation on the fly. Always add.
        # - JSONField: these are provided as FIELDNAME__SOME_DATA, so won't match directly. Just let the whole thing through.
        # - Anything using NamedSourceWidget: these lookup columns might not match the form field.
        # - Anything using CompositeLookupWidget: these lookup columns might not always mention the form field target.
        # - NamedSourceWidget or CompositeLookupWidget mentioned within a SourceFieldSwitcher.
        # - Fields defined as attributes on the importer, but not listed as form fields (eg because they're used for postprocessing).
        header_set = set(self.headers)
        virtual_fields = []
        for field_name, field_class in self.modelimportformclass.base_fields.items():
            if isinstance(field_class, FlatRelatedField | JSONField):
                virtual_fields.append(field_name)
            elif isinstance(field_class.widget, NamedSourceWidget):
                if field_class.widget.source in header_set:
                    virtual_fields.append(field_name)
            elif isinstance(field_class.widget, CompositeLookupWidget):
                if set(field_class.widget.source) < header_set:
                    virtual_fields.append(field_name)
            elif isinstance(field_class, SourceFieldSwitcher):
                for switch_field_class in field_class.fields:
                    if isinstance(switch_field_class.widget, NamedSourceWidget):
                        if switch_field_class.widget.source in header_set:
                            virtual_fields.append(field_name)
                    elif isinstance(field_class.widget, CompositeLookupWidget):
                        if set(field_class.widget.source) < header_set:
                            virtual_fields.append(field_name)

        return valid_present_fields + list(set(virtual_fields) - set(valid_present_fields))

    @cached_property
    def required_fields(self):
        fields = self.model._meta.get_fields()
        required_fields = []

        # Required means `blank` is False and `editable` is True.
        for f in fields:
            # Note - if the field doesn't have a `blank` attribute it is probably
            # a ManyToOne relation (reverse foreign key), which you probably want to ignore.
            if getattr(f, 'blank', True) is False and getattr(f, 'editable', True) is True and f.default is NOT_PROVIDED:
                required_fields.append(f.name)
        return required_fields

    def _get_modelimport_form_class(self, fields):
        """ Return a modelform for use with this data.

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