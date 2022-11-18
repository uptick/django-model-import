from django.db import transaction

from .caches import SimpleDictCache
from .formclassbuilder import FormClassBuilder
from .resultset import ImportResultSet


class ModelImporter:
    """A base class which parses and processes a CSV import, and handles the priming of any required caches."""

    def __init__(self, modelimportformclass) -> None:
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
        return (
            self.update_cache[pk]
            if self.update_cache
            else self.update_queryset.get(pk=pk)
        )

    @transaction.atomic
    def process(
        self,
        headers,
        rows,
        commit=False,
        allow_update=True,
        allow_insert=True,
        limit_to_queryset=None,
        author=None,
        progress_logger=None,
        skip_func=None,
        resultset_cls=ImportResultSet,
    ):
        """Process the data.

        @param limit_to_queryset A queryset which limits the instances which can be updated, and creates a cache of the
            updatable records to improve update performance.
        """
        # Set up a cache context which will be filled by the Cached fields
        caches = SimpleDictCache()

        # Set up an "update" cache to preload any objects which might be updated
        if allow_update:
            self.update_queryset = (
                limit_to_queryset
                if limit_to_queryset is not None
                else self.model.objects.all()
            )
            # We only build the update_cache if limit_to_queryset is provided, with the assumption that the dataset
            # is then not too big. This may not be a valid assumption.
            # @todo Could we be smarter about the update cache, e.g. iterate through the source row PKs
            self.update_cache = {}
            if limit_to_queryset is not None:
                for obj in self.update_queryset:
                    self.update_cache[str(obj.id)] = obj

        formclassbuilder = FormClassBuilder(self.modelimportformclass, headers)

        # Create a Form for rows where we are doing an UPDATE (required fields only relevant if attempting to wipe them).
        ModelUpdateForm = formclassbuilder.build_update_form()

        # Create a Form for rows where doing an INSERT (includes required fields).
        ModelCreateForm = formclassbuilder.build_create_form()

        # Create form to pass context to the ImportResultSet
        # TODO: evaluate this, only added because of FlatRelatedField
        header_form = ModelCreateForm(data={}, caches={}, author=author)
        importresult = resultset_cls(headers=headers, header_form=header_form)

        sid = transaction.savepoint()

        # Start processing
        created = updated = skipped = failed = 0
        for i, row in enumerate(rows, start=1):
            errors = []
            warnings = []
            instance = None
            to_be_created = (
                row.get("id", "") == ""
            )  # If ID is blank we are creating a new row, otherwise we are updating
            to_be_updated = not to_be_created
            to_be_skipped = skip_func(row) if skip_func else False
            import_form_class = ModelCreateForm if to_be_created else ModelUpdateForm

            # Evaluate skip first
            # So that the import doesn't die for no reason
            if to_be_skipped:
                skipped += 1
                continue

            if to_be_created and not allow_insert:
                errors = [("id", ["Creating new rows is not permitted"])]
                importresult.append(i, row, errors, instance, to_be_created)
                continue

            if to_be_updated and not allow_update:
                errors = [("id", ["Updating existing rows is not permitted"])]
                importresult.append(i, row, errors, instance, to_be_created)
                continue

            if to_be_updated:
                try:
                    instance = self.get_for_update(row["id"])
                except self.model.DoesNotExist:
                    errors = [
                        (
                            "id",
                            [
                                f'{self.model._meta.verbose_name.title()} {row["id"]} does not exist.'
                            ],
                        )
                    ]
                except KeyError:
                    errors = [
                        (
                            "id",
                            [
                                f'{self.model._meta.verbose_name.title()} {row["id"]} cannot be updated.'
                            ],
                        )
                    ]

            if not errors:
                form = import_form_class(
                    row, caches=caches, instance=instance, author=author
                )
                if form.is_valid():
                    try:
                        with transaction.atomic():
                            instance = form.save(commit=commit)

                        if to_be_created:
                            created += 1
                        if to_be_updated:
                            updated += 1
                    except Exception as err:
                        errors = [(i, repr(err))]

                else:
                    # TODO: Filter out errors associated with FlatRelatedField
                    errors = list(form.errors.items())

                warnings = list(form.warnings.items())

            if not instance or not instance.pk or errors:
                failed += 1

            result_row = importresult.append(
                i, row, errors, instance, to_be_created, warnings
            )
            if progress_logger:
                progress_logger(result_row)

        if commit:
            transaction.savepoint_commit(sid)
        else:
            transaction.savepoint_rollback(sid)

        importresult.set_counts(
            created=created, updated=updated, skipped=skipped, failed=failed
        )
        return importresult
