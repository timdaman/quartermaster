"""quartermaster URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from importlib import import_module

from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', RedirectView.as_view(url='/gui/resource/'), name='index'),
]

# Automatically register all enabled apps
for app in settings.INSTALLED_APPS:
    if app.startswith('django.contrib.'):
        continue
    app_shortname = app.split('.')[-1]
    try:
        _module = import_module(f"{app}.urls")
    except:
        pass
    else:
        urlpatterns.insert(0,path(f"{app_shortname}/", include(f"{app_shortname}.urls")))
