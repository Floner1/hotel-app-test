import json


def text_overrides(request):
    """
    Inject all inline-edit text overrides into every template context as JSON.
    Keys with ':' are inline-edit overrides (page:tag:hash format).
    Embedded in the page so JS can apply them instantly with no AJAX flash.
    """
    try:
        from data.models.site_content import SiteContent
        entries = SiteContent.objects.filter(content_key__contains=':')
        overrides = {c.content_key: c.content_value for c in entries}
        return {
            'text_overrides_json': json.dumps(overrides, ensure_ascii=False),
            'is_admin_user': (
                request.user.is_authenticated
                and hasattr(request.user, 'role')
                and request.user.role in ('admin', 'staff')
            ),
        }
    except Exception:
        return {
            'text_overrides_json': '{}',
            'is_admin_user': False,
        }
