"""Guards the static/ vendor cleanup.

Half (a) pins the dead assets as deleted so nobody re-adds them by dragging an
old theme bundle back in. Half (b) pins the live ones as present so an
over-eager future cleanup cannot take an asset base.html actually loads.
"""

from pathlib import Path

import pytest

SITE1 = Path(__file__).resolve().parent.parent

# Dead vendor assets: nothing outside this list referenced them. The four
# ionicons fonts were reachable only from css/ionicons.min.css, which is itself
# dead and listed here.
DEAD = [
    "static/css/bootstrap.css",
    "static/css/bootstrap.css.map",
    "static/css/ionicons.min.css",
    "static/css/animate.css",
    "static/css/jquery.timepicker.css",
    "static/js/jquery.timepicker.min.js",
    "static/js/jquery.stellar.min.js",
    "static/fonts/ionicons.svg",
    "static/fonts/ionicons.ttf",
    "static/fonts/ionicons.eot",
    "static/fonts/ionicons.woff",
]

# Loaded by templates/base.html, or reached from a stylesheet it loads.
LIVE = [
    "static/css/bootstrap.min.css",
    "static/css/bootstrap-datepicker.css",
    "static/css/font-awesome.min.css",
    "static/css/style.css",
    "static/css/overrides.css",
    "static/css/chat-widget.css",
    "static/css/admin-edit.css",
    "static/fonts/fontawesome-webfont.eot",
    "static/fonts/fontawesome-webfont.svg",
    "static/fonts/fontawesome-webfont.ttf",
    "static/fonts/fontawesome-webfont.woff",
    "static/fonts/fontawesome-webfont.woff2",
    "static/js/jquery-3.3.1.min.js",
    "static/js/jquery-migrate-3.0.1.min.js",
    "static/js/popper.min.js",
    "static/js/bootstrap.min.js",
    "static/js/bootstrap-datepicker.js",
    "static/js/main.js",
    "static/js/chat-widget.js",
    "static/js/admin-edit.js",
]


@pytest.mark.parametrize("rel", DEAD)
def test_dead_asset_is_gone(rel):
    assert not (SITE1 / rel).exists(), f"{rel} is dead vendor weight; delete it"


@pytest.mark.parametrize("rel", LIVE)
def test_live_asset_survives(rel):
    assert (SITE1 / rel).exists(), f"{rel} is loaded at runtime; do not delete it"
