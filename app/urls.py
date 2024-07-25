from django.contrib import admin
from django.urls import path
from django.views.generic.base import RedirectView
from django.conf.urls import include

urlpatterns = [
    path('bot/', RedirectView.as_view(url='/', permanent=False)),
    path("i18n/", include("django.conf.urls.i18n")),
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=True)),
    path('', admin.site.urls),
]
