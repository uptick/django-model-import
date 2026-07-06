from django.contrib import admin

from testapp.models import Author


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    pass
