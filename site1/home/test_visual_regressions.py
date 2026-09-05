"""Regression tests for batch-4 visual findings.

These parse the CSS that actually ships, so a revert to a failing value fails the
suite. Restating the expected value as a constant would only test the constant.
"""
import re
from pathlib import Path

import pytest

from home.test_contrast import contrast_ratio, parse_color

CSS_DIR = Path(__file__).resolve().parent.parent / "static" / "css"
STYLE_CSS = CSS_DIR / "style.css"
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def rule_bodies(css_text, selector):
    """Every declaration block whose selector list contains `selector` exactly.

    Returns a list because a selector legitimately appears more than once (base
    rule plus media-query overrides), and the finding is about the union of them.
    """
    bodies = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css_text):
        selectors = [s.strip() for s in match.group(1).split(",")]
        if selector in selectors:
            bodies.append(match.group(2))
    return bodies


def declared(body, prop):
    """Value of `prop` in a declaration block, or None."""
    match = re.search(rf"(?:^|;)\s*{re.escape(prop)}\s*:\s*([^;]+)", body)
    return match.group(1).strip() if match else None


@pytest.fixture(scope="module")
def style_css():
    return STYLE_CSS.read_text(encoding="utf-8")


# A var() reference with no comma has no fallback: if the property is undefined the
# declaration is invalid at computed-value time and the style silently does nothing.
VAR_NO_FALLBACK = re.compile(r"var\(\s*(--[\w-]+)\s*\)")
VAR_DEFINITION = re.compile(r"(--[\w-]+)\s*:")


def shipped_sources():
    """Every stylesheet and template the browser actually receives.

    Minified vendor bundles are excluded: they ship their own variables and are not
    ours to police.
    """
    files = [p for p in CSS_DIR.glob("*.css") if ".min." not in p.name]
    files += sorted(TEMPLATE_DIR.rglob("*.html"))
    return files


def test_no_custom_property_is_used_without_being_defined():
    defined = set()
    used = {}
    for path in shipped_sources():
        text = path.read_text(encoding="utf-8")
        defined.update(VAR_DEFINITION.findall(text))
        for name in VAR_NO_FALLBACK.findall(text):
            used.setdefault(name, path.name)

    missing = {name: src for name, src in used.items() if name not in defined}
    assert not missing, (
        "custom properties used with no fallback and never defined: "
        + ", ".join(f"{n} (first seen in {s})" for n, s in sorted(missing.items()))
    )


# The WCAG maths lives in test_contrast.py, which parses colours out of the
# shipped CSS for the accessibility fixes. It works in rgb tuples; these call
# sites hold hex strings, so parse_color bridges the two.
def contrast_ratio_hex(fg, bg):
    return contrast_ratio(parse_color(fg)[0], parse_color(bg)[0])


@pytest.mark.parametrize("background", ["#ffffff", "#f9fafb"])
def test_muted_token_clears_aa_on_its_backgrounds(style_css, background):
    """--color-muted now paints text that previously just inherited. Every call site
    sits on white or the surface tint, so both have to clear 4.5:1."""
    root = rule_bodies(style_css, ":root")[0]
    alias = declared(root, "--color-muted")
    assert alias == "var(--color-text-muted)", f"unexpected --color-muted value: {alias}"
    resolved = declared(root, "--color-text-muted")
    assert contrast_ratio_hex(resolved, background) >= 4.5, (
        f"muted text {resolved} on {background} is "
        f"{contrast_ratio_hex(resolved, background):.2f}:1, below AA"
    )


# ── Room Rates naming consistency ──────────────────────────────────────────
# The audit pointed at rooms.html:273, but that line renders {{ room.display }}.
# The label is derived in HotelService.get_available_room_types from the
# room_price.room_type column, so the inconsistency is in the data and the fix
# belongs where the label is built. canonical must survive untouched: it is the
# matching key for rates, availability, and existing bookings.

SEEDED_ROOM_TYPES = [
    "1 Bed No Window",
    "2 Bed No Window Room",  # the lone outlier carrying a trailing "Room"
    "1 Bed With Window",
    "1 Bed With Balcony",
    "2 Bed & Balcony Condotel",
]


@pytest.fixture
def seeded_rates(hotel):
    from decimal import Decimal

    from data.models import RoomPrice

    return [
        RoomPrice.objects.create(
            hotel=hotel, room_type=name, price_per_night=Decimal("650000")
        )
        for name in SEEDED_ROOM_TYPES
    ]


@pytest.mark.django_db
def test_room_display_names_are_consistently_suffixed(seeded_rates):
    from backend.services.services import HotelService

    displays = [r["display"] for r in HotelService.get_available_room_types()]
    offenders = [d for d in displays if d.endswith(" Room")]
    assert not offenders, (
        f"room labels disagree about the trailing 'Room': {offenders} carry it "
        f"while the rest of {displays} do not"
    )


@pytest.mark.django_db
def test_normalising_the_display_name_leaves_canonical_untouched(seeded_rates):
    """canonical is the rate/availability matching key and is stored on existing
    bookings. Tidying the label must not touch it."""
    from backend.services.services import HotelService

    canonicals = {r["canonical"] for r in HotelService.get_available_room_types()}
    assert "2 Bed No Window Room" in canonicals, (
        "canonical was rewritten; rate matching and historical bookings would break"
    )


@pytest.mark.django_db
def test_a_room_type_that_is_only_room_still_gets_a_label(hotel):
    """Stripping the suffix must never leave an empty option in the dropdown."""
    from decimal import Decimal

    from backend.services.services import HotelService
    from data.models import RoomPrice

    RoomPrice.objects.create(
        hotel=hotel, room_type="_room", price_per_night=Decimal("1")
    )
    displays = [r["display"] for r in HotelService.get_available_room_types()]
    assert all(d.strip() for d in displays), f"blank room label rendered: {displays!r}"
