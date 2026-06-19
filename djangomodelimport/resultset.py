from collections.abc import Collection
from typing import TYPE_CHECKING

from django.db import models

from djangomodelimport.types import Data, FieldErrorList

if TYPE_CHECKING:
    from djangomodelimport import ImporterModelForm


class ImportResultSet[Model: models.Model, Author]:
    """Hold all imported results."""

    def __init__(
        self, headers: Collection[str], header_form: "ImporterModelForm[Model, Author]"
    ) -> None:
        self.results: list[ImportResultRow] = []
        self.headers: Collection[str] = headers
        self.header_form: ImporterModelForm[Model, Author] = header_form
        self.created: int = 0
        self.updated: int = 0
        self.skipped: int = 0
        self.failed: int = 0

    def __repr__(self) -> str:
        total = len(self.results)
        errors = len(self.get_errors())
        warnings = len(self.get_warnings())
        return f"ImportResultSet ({total} rows, {errors} errors, {warnings} warnings)"

    def append(
        self,
        index: int,
        row: Data,
        errors: FieldErrorList,
        instance: Model | None,
        created: bool,
        warnings: FieldErrorList | None = None,
    ) -> "ImportResultRow":
        result_row = ImportResultRow(self, index, row, errors, instance, created, warnings)
        self.results.append(result_row)
        return result_row

    def get_import_headers(self) -> list[str]:
        return self.header_form.get_headers(self.headers)

    def get_results(self) -> list["ImportResultRow"]:
        return self.results

    def get_errors(self) -> list[tuple[int, FieldErrorList]]:
        return [(row.linenumber, row.errors) for row in self.results if not row.is_valid()]

    def get_warnings(self) -> list[tuple[int, FieldErrorList]]:
        return [(row.linenumber, row.warnings) for row in self.results if row.warnings]

    def set_counts(self, created: int, updated: int, skipped: int, failed: int) -> None:
        self.created = created
        self.updated = updated
        self.skipped = skipped
        self.failed = failed

    def get_counts(self) -> tuple[int, int, int, int]:
        return self.created, self.updated, self.skipped, self.failed


class ImportResultRow[Model: models.Model, Author]:
    """Hold the result of an imported row."""

    def __init__(
        self,
        resultset: ImportResultSet,
        linenumber: int,
        row: Data,
        errors: FieldErrorList,
        instance: Model | None,
        created: bool,
        warnings: FieldErrorList | None = None,
    ):
        self.resultset: ImportResultSet[Model, Author] = resultset
        self.linenumber: int = linenumber
        self.row: Data = row
        self.errors: FieldErrorList = list(errors)
        self.instance: Model | None = instance
        self.created: bool = created
        self.warnings: FieldErrorList = list(warnings) if warnings else []

    def __repr__(self) -> str:
        valid_str = "valid" if self.is_valid() else "invalid"
        mode_str = "create" if self.created else "update"
        res = self.get_instance_values() if self.is_valid() else self.errors
        sample = str([(k, v) for k, v in self.row.items()])[:100]
        return f"{self.linenumber}. [{valid_str}] [{mode_str}] ... {sample} ... {res}"

    def get_instance_values(self) -> list:
        return self.resultset.header_form.get_instance_values(
            self.instance, self.resultset.get_import_headers()
        )

    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def get_errors(self) -> FieldErrorList:
        return list(self.errors)
