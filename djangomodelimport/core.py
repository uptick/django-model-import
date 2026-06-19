from collections.abc import Callable, MutableMapping, Sequence
from typing import Any, cast

from django.db import models, transaction
from django.db.models import QuerySet
from django.forms.utils import ErrorList

from djangomodelimport.caches import SimpleDictCache
from djangomodelimport.exceptions import InvalidFormException
from djangomodelimport.formclassbuilder import FormClassBuilder
from djangomodelimport.forms import ImporterModelForm
from djangomodelimport.resultset import ImportResultRow, ImportResultSet
from djangomodelimport.types import Data, FieldErrorList


class ModelImporter[Model: models.Model, Form: ImporterModelForm]:
    """A base class which parses and processes a CSV import, and handles the priming of any required caches."""

    def __init__(self, modelimportformclass: type[Form]) -> None:
        """
        @param modelimportformclass The ImporterModelForm class (which extends a simple ModelForm)
        """
        self.instances: Sequence[Model] = []
        self.errors: FieldErrorList = []
        self.modelimportformclass: type[Form] = modelimportformclass
        if modelimportformclass._meta.model is None:
            raise InvalidFormException("ImporterModelForm must be bound to a model")
        self.model: type[Model] = cast("type[Model]", modelimportformclass._meta.model)
        self.update_cache: MutableMapping[str, Model] | None = None
        self.update_queryset: QuerySet[Model] = self.model.objects.none()
        self._model_verbose_name = (self.model._meta.verbose_name or self.model.__name__).title()

    def get_for_update(self, pk: Any) -> Model:
        if self.update_cache:
            return self.update_cache[pk]
        return self.update_queryset.get(pk=pk)

    @transaction.atomic
    def process[ResultSet: ImportResultSet, Author](
        self,
        headers: Sequence[str],
        rows: Sequence[Data],
        commit: bool = False,
        allow_update: bool = True,
        allow_insert: bool = True,
        limit_to_queryset: QuerySet[Model] | None = None,
        author: Author | None = None,
        progress_logger: Callable[[ImportResultRow], ...] | None = None,
        skip_func: Callable[..., bool] | None = None,
        resultset_cls: type[ResultSet] = ImportResultSet,
    ) -> ResultSet:
        """Process the data.

        @param limit_to_queryset A queryset which limits the instances which can be updated, and creates a cache of the
            updatable records to improve update performance.
        """
        # Set up a cache context which will be filled by the Cached fields
        caches = SimpleDictCache()

        # Set up an "update" cache to preload any objects which might be updated
        if allow_update:
            self.update_queryset = (
                limit_to_queryset if limit_to_queryset is not None else self.model.objects.all()
            )
            # We only build the update_cache if limit_to_queryset is provided, with the assumption that the dataset
            # is then not too big. This may not be a valid assumption.
            # @todo Could we be smarter about the update cache, e.g. iterate through the source row PKs
            self.update_cache = {}
            if limit_to_queryset is not None:
                for obj in self.update_queryset:
                    self.update_cache[str(obj.id)] = obj  # type: ignore[missing-attribute]

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
        created: int = 0
        updated: int = 0
        skipped: int = 0
        failed: int = 0
        for i, row in enumerate(rows, start=1):
            errors: FieldErrorList = []
            warnings: FieldErrorList = []
            instance: Model | None = None
            to_be_created: bool = (
                row.get("id", "") == ""
            )  # If ID is blank we are creating a new row, otherwise we are updating
            to_be_updated: bool = not to_be_created
            to_be_skipped: bool = skip_func(row) if skip_func else False
            import_form_class: type[Form] = ModelCreateForm if to_be_created else ModelUpdateForm

            # Evaluate skip first
            # So that the import doesn't die for no reason
            if to_be_skipped:
                skipped += 1
                continue

            if to_be_created and not allow_insert:
                errors = [("id", ErrorList(["Creating new rows is not permitted"]))]
                importresult.append(i, row, errors, instance, to_be_created)
                continue

            if to_be_updated and not allow_update:
                errors = [("id", ErrorList(["Updating existing rows is not permitted"]))]
                importresult.append(i, row, errors, instance, to_be_created)
                continue

            if to_be_updated:
                try:
                    instance = self.get_for_update(row["id"])
                except ValueError as e:
                    # We cannot validate an id's format until we try to fetch it from the DB
                    if "expected a number" in str(e):
                        errors = [
                            (
                                "id",
                                ErrorList(
                                    [
                                        f"{self._model_verbose_name} {row['id']} is an invalid format for an ID."
                                    ]
                                ),
                            )
                        ]
                    else:
                        raise e
                except self.model.DoesNotExist:
                    errors = [
                        (
                            "id",
                            ErrorList([f"{self._model_verbose_name} {row['id']} does not exist."]),
                        )
                    ]
                except KeyError:
                    errors = [
                        (
                            "id",
                            ErrorList(
                                [f"{self._model_verbose_name} {row['id']} cannot be updated."]
                            ),
                        )
                    ]

            if not errors:
                form = import_form_class(row, caches=caches, instance=instance, author=author)
                if form.is_valid():
                    try:
                        with transaction.atomic():
                            instance = form.save(commit=commit)

                        if to_be_created:
                            created += 1
                        if to_be_updated:
                            updated += 1
                    except Exception as err:
                        errors = [(str(i), ErrorList([repr(err)]))]

                else:
                    # TODO: Filter out errors associated with FlatRelatedField
                    errors = [
                        (k, ErrorList([str(err) for err in v])) for k, v in form.errors.items()
                    ]

                warnings = list(form.warnings.items())

            if not instance or not instance.pk or errors:
                failed += 1

            result_row = importresult.append(i, row, errors, instance, to_be_created, warnings)
            if progress_logger:
                progress_logger(result_row)

        if commit:
            transaction.savepoint_commit(sid)
        else:
            transaction.savepoint_rollback(sid)

        importresult.set_counts(created=created, updated=updated, skipped=skipped, failed=failed)
        return importresult
