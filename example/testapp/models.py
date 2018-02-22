from jsonfield import JSONField

from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Book(models.Model):
    name = models.CharField(max_length=100)
    author = models.ForeignKey(Author)

    def __str__(self):
        return self.name


class Citation(models.Model):
    name = models.CharField(max_length=100)
    author = models.ForeignKey(Author)

    # Add a JSON field (SQLite only supports TextField, but this should work with JSONField or HStoreField)
    # Setting blank=True is important here to make sure we're testing for:
    # this issue, https://github.com/uptick/django-model-import/issues/9
    metadata = JSONField()

    def __str__(self):
        return self.name
