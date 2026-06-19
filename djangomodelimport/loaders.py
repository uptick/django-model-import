from collections.abc import Collection
from typing import Any, cast

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import models


class CachedInstanceLoader[Model: models.Model](
    dict[str, Model | ObjectDoesNotExist | MultipleObjectsReturned]
):
    """A clever cache that queries the database for any missing objects.

    If there's an error, it's only raised against the first item that causes it, then it's
    cached for extra speed.
    """

    def __init__(
        self,
        queryset: models.QuerySet[Model],
        to_field: str | Collection[str],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.queryset: models.QuerySet[Model] = queryset
        self.model: type[Model] = queryset.model
        self.to_field: str | Collection[str] = to_field
        self.multifield: bool = isinstance(to_field, list) or isinstance(to_field, tuple)
        super().__init__(*args, **kwargs)

    def __getitem__(self, item: str) -> Model:
        # Attempt to get the currently cached value.
        value = super().__getitem__(item)

        # If the cached value is an error, re-raise
        if isinstance(value, Exception):
            raise value

        return value

    def __missing__(self, value: str) -> Model:
        if self.multifield:
            params = dict(zip(cast("Collection[str]", self.to_field), value, strict=False))
        else:
            params = {cast("str", self.to_field): value}

        try:
            self[value] = inst = self.queryset.get(**params)
        except self.model.DoesNotExist as err:
            self[value] = err  # Further warnings will be re-raised
            raise
        except self.model.MultipleObjectsReturned as err:
            self[value] = err  # Further warnings will be re-raised
            raise
        return inst
