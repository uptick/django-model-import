from django.db import transaction
from django.db.models.fields import NOT_PROVIDED
from django.forms import modelform_factory

from .caches import SimpleDictCache


class ModelImporter:
    """ A base class which parses and processes a CSV import, and handles the priming of any required caches. """
    def __init__(self, modelimportformclass):
        self.instances = []
        self.errors = []
        self.modelimportformclass = modelimportformclass
        self.model = modelimportformclass.Meta.model

    def get_valid_fields(self, headers):
        """ Return a list of valid fields for this importer, in the order they
        appear in the input file.
        """
        return [field for field in headers if field in self.modelimportformclass.Meta.fields]

    def get_required_fields(self):
        fields = self.model._meta.get_fields()
        required_fields = []

        # Required means `blank` is False and `editable` is True.
        for f in fields:
            # Note - if the field doesn't have a `blank` attribute it is probably
            # a ManyToOne relation (reverse foreign key), which you probably want to ignore.
            if getattr(f, 'blank', True) is False and getattr(f, 'editable', True) is True and f.default is NOT_PROVIDED:
                required_fields.append(f.name)
        return required_fields

    def get_modelimport_form_class(self, fields):
        """ Return a modelform for use with this data.

        We use a modelform_factory to dynamically limit the fields on the import,
        otherwise the absence of a value can be taken as false for boolean fields,
        where as we want the model's default value to kick in.
        """
        return modelform_factory(
            self.model,
            form=self.modelimportformclass,
            fields=fields,
        )

    @transaction.atomic
    def process(self, headers, rows, commit=False):
        # Set up a cache context which will be filled by the Cached fields
        caches = SimpleDictCache()

        valid_fields = self.get_valid_fields(headers)

        # Create a Form (using modelform_factory) for rows where we are doing an UPDATE
        ModelUpdateForm = self.get_modelimport_form_class(fields=valid_fields)

        # Create a Form for rows where doing an INSERT, make sure to include the required fields
        # Combine valid & required fields; preserving order of valid fields.
        form_fields = valid_fields + list(set(self.get_required_fields()) - set(valid_fields))
        ModelImportForm = self.get_modelimport_form_class(fields=form_fields)

        # Create form for things?
        header_form = ModelImportForm(data={}, caches={})
        importresult = ImportResultSet(headers=headers, header_form=header_form)

        sid = transaction.savepoint()

        # Start processing
        for i, row in enumerate(rows, start=1):
            errors = []
            instance = None
            created = row.get('id', '') == ''  # If ID is blank we are creating a new row, otherwise we are updating
            import_form_class = ModelImportForm if created else ModelUpdateForm

            if not created:
                try:
                    instance = self.model.objects.get(id=row['id'])
                except self.model.DoesNotExist:
                    errors = [('', 'No %s with id %s.' % (self.model._meta.verbose_name.title(), row['id']))]

            if not errors:
                form = import_form_class(row, caches, instance=instance)
                if form.is_valid():
                    instance = form.save(commit=commit)
                else:
                    # TODO: Filter out errors associated with FlatRelatedField
                    errors = list(form.errors.items())
            importresult.append(i, row, errors, instance, created)

        if commit:
            transaction.savepoint_commit(sid)
        else:
            transaction.savepoint_rollback(sid)

        return importresult


class ImportResultSet:
    """ Hold all imported results. """
    def __init__(self, headers, header_form):
        self.results = []
        self.headers = headers
        self.header_form = header_form

    def __str__(self):
        return '{} {}'.format(self.get_import_headers(), self.results)

    def append(self, index, row, errors, instance, created):
        self.results.append(
            ImportResultRow(self, index, row, errors, instance, created)
        )

    def get_import_headers(self):
        return self.header_form.get_headers(self.headers)

    def get_results(self):
        return self.results

    def get_errors(self):
        return [(row.linenumber, row.errors) for row in self.results if not row.is_valid()]


class ImportResultRow:
    """ Hold the result of an imported row. """
    def __init__(self, resultset, linenumber, row, errors, instance, created):
        self.resultset = resultset
        self.linenumber = linenumber
        self.row = row
        self.errors = errors
        self.instance = instance
        self.created = created

    def __str__(self):
        return '{} {}'.format(self.linenumber, self.row)

    def get_instance_values(self):
        return self.resultset.header_form.get_instance_values(self.instance, self.resultset.get_import_headers())

    def is_valid(self):
        return len(self.errors) == 0
