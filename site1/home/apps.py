from django.apps import AppConfig


class HomeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'home'

    def ready(self):
        # `runserver` with no address:port arg binds/prints `localhost`
        # instead of `127.0.0.1`. Some browser/security config on this
        # machine forces HTTPS on bare IP literals like 127.0.0.1 but not
        # on the `localhost` hostname (unresolved which layer does it —
        # ruled out Chrome settings, system proxy, known TLS-intercepting
        # processes). django.contrib.staticfiles provides the actual
        # runserver command in this project (it wraps the base one to also
        # serve static files in DEBUG), so patch its default_addr directly
        # rather than adding a same-named command in this app — app-level
        # overrides lose to staticfiles' here because of INSTALLED_APPS
        # order in django.core.management.get_commands().
        from django.contrib.staticfiles.management.commands.runserver import (
            Command as StaticfilesRunserverCommand,
        )
        StaticfilesRunserverCommand.default_addr = 'localhost'
