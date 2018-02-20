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
    metadata = models.TextField()  # Use models.JSONField if your database supports it

    def __str__(self):
        return self.name
