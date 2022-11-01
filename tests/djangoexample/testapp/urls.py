from django.contrib import admin
from django.urls import path

from .views import CitationCreateView, TestImportView

urlpatterns = [
    path(r"^admin/", admin.site.urls),
    path(r"^$", TestImportView.as_view(), name="start"),
    path(r"^create/$", CitationCreateView.as_view(), name="create"),
]
