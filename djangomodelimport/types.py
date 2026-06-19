from collections.abc import MutableMapping

from django.contrib.auth import models
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.forms.utils import ErrorList

type Cache[Instance: models.Model] = MutableMapping[
    str, Instance | ObjectDoesNotExist | MultipleObjectsReturned
]
type Data = dict[str, str | float | bool | None]
type FieldErrorList = list[tuple[str, ErrorList]]
