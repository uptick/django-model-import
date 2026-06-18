from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Book(models.Model):
    name = models.CharField(max_length=100)
    author = models.ForeignKey(Author, on_delete=models.PROTECT)

    def __str__(self):
        return self.name


class Citation(models.Model):
    name = models.CharField(max_length=100)
    author = models.ForeignKey(Author, on_delete=models.PROTECT)
    metadata = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=1000)
    mobile = models.CharField(max_length=50)
    address = models.TextField()

    def __str__(self):
        return self.name


class Company(models.Model):
    name = models.CharField(max_length=100)
    primary_contact = models.ForeignKey(Contact, on_delete=models.PROTECT)

    def __str__(self):
        return self.name
