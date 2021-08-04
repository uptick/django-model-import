from django.db import transaction
from django.db.models.fields import NOT_PROVIDED
from django.forms import modelform_factory

from .caches import SimpleDictCache


class ModelImporter:
    """ A base class which parses and processes a CSV import, and handles the priming of any required caches. """
    def __init__(self, modelimportformclass):
        """
        @param modelimportformclass The ImporterModelForm class (which extends a simple ModelForm)
        """
        self.instances = []
        self.errors = []
        self.modelimportformclass = modelimportformclass
        self.model = modelimportformclass.Meta.model
        self.update_cache = None
        self.update_queryset = None

    def get_for_update(self, pk):
        return self.update_cache[pk] if self.update_cache else self.update_queryset.get(pk=pk)

    def get_valid_fields(self, headers):
        """ Return a list of valid fields for this importer, in the order they
        appear in the input file.
        """
        valid_present_fields = [field for field in headers if field in self.modelimportformclass.base_fields]
        virtual_fields = getattr(self.modelimportformclass.Meta, 'virtual_fields', [])  # See https://github.com/uptick/django-model-import/issues/9
        return valid_present_fields + list(virtual_fields)

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
        klass = modelform_factory(
            self.model,
            form=self.modelimportformclass,
            fields=fields,
        )
        base_fields_to_del = set(klass.base_fields.keys()) - set(fields)
        for f in base_fields_to_del:
            del klass.base_fields[f]
        return klass


    @transaction.atomic
    def process(self, headers, rows, commit=False, allow_update=True, allow_insert=True, limit_to_queryset=None, author=None, progress_logger=None):
        """

        @param limit_to_queryset A queryset which limits the instances which can be updated, and creates a cache of the
            updatable records to improve update performance.
        """
        # Set up a cache context which will be filled by the Cached fields
        caches = SimpleDictCache()

        # Set up an "update" cache to preload any objects which might be updated
        if allow_update:
            self.update_queryset = limit_to_queryset if limit_to_queryset is not None else self.model.objects.all()
            # We only build the update_cache if limit_to_queryset is provided, with the assumption that the dataset
            # is then not too big. This may not be a valid assumption.
            # @todo Could we be smarter about the update cache, e.g. iterate through the source row PKs
            self.update_cache = {}
            if limit_to_queryset is not None:
                for obj in self.update_queryset:
                    self.update_cache[str(obj.id)] = obj

        valid_fields = self.get_valid_fields(headers)

        # Create a Form (using modelform_factory) for rows where we are doing an UPDATE
        ModelUpdateForm = self.get_modelimport_form_class(fields=valid_fields)

        # Create a Form for rows where doing an INSERT, make sure to include the required fields
        # Combine valid & required fields; preserving order of valid fields.
        form_fields = valid_fields + list(set(self.get_required_fields()) - set(valid_fields))
        ModelImportForm = self.get_modelimport_form_class(fields=form_fields)

        # Create form to pass context to the ImportResultSet
        # TODO: evaluate this, only added because of FlatRelatedField
        header_form = ModelImportForm(data={}, caches={}, author=author)
        importresult = ImportResultSet(headers=headers, header_form=header_form)

        sid = transaction.savepoint()

        # Start processing
        for i, row in enumerate(rows, start=1):
            errors = []
            instance = None
            to_be_created = row.get('id', '') == ''  # If ID is blank we are creating a new row, otherwise we are updating
            to_be_updated = not to_be_created
            import_form_class = ModelImportForm if to_be_created else ModelUpdateForm

            if to_be_created and not allow_insert:
                errors = [('', 'Creating new rows is not permitted')]
                importresult.append(i, row, errors, instance, to_be_created)
                continue

            if to_be_updated and not allow_update:
                errors = [('', 'Updating existing rows is not permitted')]
                importresult.append(i, row, errors, instance, to_be_created)
                continue

            if to_be_updated:
                try:
                    instance = self.get_for_update(row['id'])
                except (self.model.DoesNotExist, KeyError):
                    errors = [('', '%s %s cannot be updated.' % (self.model._meta.verbose_name.title(), row['id']))]

            if not errors:
                form = import_form_class(row, caches=caches, instance=instance, author=author)
                if form.is_valid():
                    instance = form.save(commit=commit)
                else:
                    # TODO: Filter out errors associated with FlatRelatedField
                    errors = list(form.errors.items())
            result_row = importresult.append(i, row, errors, instance, to_be_created)
            if progress_logger:
                progress_logger(result_row)

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

    def __repr__(self):
        return f'ImportResultSet ({len(self.results)} rows, {len(self.get_errors())} errors)'

    def append(self, index, row, errors, instance, created):
        result_row = ImportResultRow(self, index, row, errors, instance, created)
        self.results.append(result_row)
        return result_row

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

    def __repr__(self):
        valid_str = "valid" if self.is_valid() else "invalid"
        mode_str = "create" if self.created else "update"
        res = self.get_instance_values() if self.is_valid() else self.errors
        sample = str([(k, v) for k, v in self.row.items()])[:100]
        return f'{self.linenumber}. [{valid_str}] [{mode_str}] ... {sample} ... {res}'

    def get_instance_values(self):
        return self.resultset.header_form.get_instance_values(self.instance, self.resultset.get_import_headers())

    def is_valid(self):
        return len(self.errors) == 0

    def get_errors(self):
        return self.errors
