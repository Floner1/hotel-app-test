"""CSP nonce coverage on inline <script> blocks.

The policy is still report-only, so nothing here proves the browser would
allow these blocks today. What it pins is the half of the flip that is done:
every inline <script> the templates ship carries a nonce, and the policy
actually declares NONCE so the attribute means something. Without the
declaration the attribute renders and the block is still refused.
"""
import re
from pathlib import Path

import pytest
from django.conf import settings

TEMPLATES = Path(settings.BASE_DIR).parent / 'templates'

# Bare <script> with no src and no nonce. src= scripts are covered by 'self'.
INLINE_NO_NONCE = re.compile(r'<script(?![^>]*\bsrc=)(?![^>]*\bnonce=)[^>]*>')


def _templates():
    return sorted(TEMPLATES.rglob('*.html'))


def test_every_inline_script_carries_a_nonce():
    offenders = []
    for path in _templates():
        # Email templates are rendered into mail, never served as a page, so
        # no browser applies a CSP to them.
        if 'email' in path.parts:
            continue
        text = path.read_text(encoding='utf-8')
        if INLINE_NO_NONCE.search(text):
            offenders.append(path.name)
    assert not offenders, f'inline <script> without a nonce: {offenders}'


def test_policy_declares_the_nonce_sentinel():
    from csp.constants import NONCE
    policy = getattr(settings, 'CONTENT_SECURITY_POLICY_REPORT_ONLY', None) \
        or settings.CONTENT_SECURITY_POLICY
    assert NONCE in policy['DIRECTIVES']['script-src'], (
        'templates carry nonce attributes but the policy never allows them')


def test_a_rendered_page_actually_emits_a_nonce(client):
    """The attribute has to survive rendering, not just exist in the file."""
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.content.decode('utf-8', 'replace')
    assert 'nonce=' in html, 'no nonce reached the rendered page'
    # The nonce in the markup must be the one the header advertises.
    header = resp.headers.get('Content-Security-Policy-Report-Only', '')
    nonce = re.search(r"'nonce-([^']+)'", header)
    assert nonce, f'policy header carries no nonce: {header!r}'
    assert f'nonce="{nonce.group(1)}"' in html, 'header nonce absent from markup'
