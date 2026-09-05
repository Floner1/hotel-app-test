"""Guards for the helpers deleted as dead code, and for the ones that must stay."""
import home.audit
from home.templatetags.email_filters import register


def test_dead_audit_helpers_are_gone():
    for name in ('log_role_change', 'get_recent_audit_logs'):
        assert not hasattr(home.audit, name), f'home.audit.{name} is back'


def test_dead_email_filters_are_unregistered():
    # static_url / inline_image were @register.simple_tag -> register.tags
    for name in ('static_url', 'inline_image'):
        assert name not in register.tags, f'{name} is still a registered simple_tag'
    # prettify_key / format_date_value were @register.filter -> register.filters
    for name in ('prettify_key', 'format_date_value'):
        assert name not in register.filters, f'{name} is still a registered filter'


def test_live_email_filters_stay_registered():
    # These four ARE used by site1/templates/email/*.html, which all
    # {% load email_filters %}. Removing them silently breaks outgoing email.
    for name in ('vietnam_time', 'vietnam_date', 'vnd', 'prettify_event'):
        assert name in register.filters, f'{name} was removed but email templates use it'
