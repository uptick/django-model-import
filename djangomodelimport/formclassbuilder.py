from collections import defaultdict
from functools import cached_property

from django.db.models.fields import NOT_PROVIDED
from django.forms import modelform_factory

from .fields import JSONField, FlatRelatedField
from .utils import ImportHeader


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
        form_fields = self.valid_fields + list(
            set(self.required_fields) - set(self.valid_fields)
        )
        return self._get_modelimport_form_class(fields=form_fields)

    @cached_property
    def valid_fields(self):
        """Using the available headers on the form, prepare a list of valid
        fields for this importer. Preserves field ordering as defined by the headers.
        """

        flat_related_fields = set()

        def _flatten_headers(
            import_headers: list[ImportHeader],
        ) -> dict[str, list[list[str]]]:
            """Take a list of importers headers and determine which fields they
            can be assigned to, flattening any alternative options for fields

            NOTE: Alternatives are only available on the first header

            Example:
                FIELD NAME : IMPORT HEADER > ALTERNATIVE HEADER COMBINATIONS
                asset: asset_id > property_ref + asset_barcode | property_ref + asset_ref
                asset: asset_type
                type: type_id > type_label
                description: description
                -- into --
                FIELD NAME : LIST OF VALID COMBINATIONS
                asset : [[asset_id, asset_type], [property_ref, asset_barcode], [property_ref, asset_ref]]
                type: [[type_id], [type_label]]
                description: [[description]]
            """
            result: dict[str, list[list[str]]] = defaultdict(lambda: [[]])
            for import_header in import_headers:
                # Track flat related fields as we only need a subset of their keys to be valid
                if isinstance(import_header.field, FlatRelatedField):
                    flat_related_fields.add(import_header.field_name)

                # Find or create field header option list
                field_list = result[import_header.field_name]

                # Add the current header name to the field list
                field_list[0].append(import_header.name)

                # For any alternatives, add them as other valid options for this field
                for alt in import_header.alternatives:
                    alt_fields = _flatten_headers(alt)
                    for k, v in alt_fields.items():
                        result[k].extend(v)

            return dict(result)

        # Get the viable headers for the importer class
        form_headers = self.modelimportformclass.get_available_headers()

        # Find all the valid field combinations
        valid_headers = _flatten_headers(form_headers)

        field_lookup = {}
        # Create a header -> field lookup dictionary
        # VALID IMPORT HEADER COMBINATIONS : FIELD NAME
        # (asset_id,): asset
        # (property_ref, asset_barcode): asset
        # (property_ref, asset_ref) : asset
        # (type_id,): type
        # (type_label,): type
        # (description,): description
        for field, header_group in valid_headers.items():
            for headers in header_group:
                field_lookup[frozenset(headers)] = field

        # See if each valid field header if in the provided import headers
        valid_present_fields = set()
        for headers, field in field_lookup.items():
            # Flat related fields only need a subset of headers to be a valid field
            if field in flat_related_fields:
                if headers & set(self.headers):
                    valid_present_fields.add(field)
            # All others need the full set of headers to be valid
            elif headers < set(self.headers):
                valid_present_fields.add(field)

        # Add an extra JSON Fields as they are wily
        for header in form_headers:
            if isinstance(header.field, JSONField):
                valid_present_fields.add(header.name)

        return list(valid_present_fields)

    @cached_property
    def required_fields(self):
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

    def _get_modelimport_form_class(self, fields):
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
