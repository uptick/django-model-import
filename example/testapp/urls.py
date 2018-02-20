from django.conf.urls import url
from django.contrib import admin

from .views import TestImportView

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', TestImportView.as_view(), name="start"),
]
