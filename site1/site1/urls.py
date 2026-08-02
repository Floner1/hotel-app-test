"""
URL configuration for site1 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django_ratelimit.exceptions import Ratelimited

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
]

def handler403(request, exception=None):
    """Return a friendly response when rate limit is exceeded."""
    if isinstance(exception, Ratelimited):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Too many requests. Please wait a moment and try again.'
            }, status=429)
        return render(request, '403_ratelimited.html', status=429)
    return render(request, '403.html', status=403)

def handler404(request, exception=None):
    return render(request, '404.html', status=404)

def handler400(request, exception=None):
    return HttpResponse(get_template('400.html').render(), status=400)

def handler500(request):
    # Rendered WITHOUT a RequestContext on purpose. render() would run every
    # context processor, and text_overrides hits the DB — a bad dependency on
    # the error path, since a dead DB is a likely reason we are here at all.
    # If a context processor ever raises, the 500 page itself 500s and the
    # user gets a bare "A server error occurred" instead of this template.
    # Today text_overrides happens to swallow its own exceptions, so this is
    # defence in depth rather than a fix for a live crash. 500.html is
    # self-contained (no extends, no tags), so it needs no context at all.
    return HttpResponse(get_template('500.html').render(), status=500)
