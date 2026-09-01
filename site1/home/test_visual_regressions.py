"""Regression tests for batch-4 visual findings.

These parse the CSS that actually ships, so a revert to a failing value fails the
suite. Restating the expected value as a constant would only test the constant.
"""
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

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


def test_popup_card_never_forces_full_viewport_height(style_css):
    bodies = rule_bodies(style_css, ".dp-card")
    assert bodies, ".dp-card rule not found in style.css"
    for body in bodies:
        height = declared(body, "height")
        assert height != "100vh", (
            "the discount popup card still pins itself to the full viewport height"
        )


def test_popup_card_is_bounded(style_css):
    bodies = rule_bodies(style_css, ".dp-card")
    values = [declared(b, "max-width") for b in bodies]
    assert any(v and v != "none" for v in values), (
        "the discount popup card has no max-width, so it spans the whole viewport"
    )


def test_popup_card_never_traps_its_own_overflow(style_css):
    """A card that both caps its height and hides its overflow strands content.

    The card is a grid whose single row is auto-sized: the row grows to its
    content and does not shrink to a capped container, so with `overflow: hidden`
    anything past the cap is clipped with no scroll path. On a short laptop that
    puts the submit button out of reach and the popup cannot be completed. The
    backdrop is the scroll container instead.
    """
    for body in rule_bodies(style_css, ".dp-card"):
        if (declared(body, "overflow") or "").startswith("hidden"):
            assert declared(body, "max-height") is None, (
                "the popup card caps its height while hiding overflow, so tall "
                "content is unreachable"
            )

    backdrop = rule_bodies(style_css, ".dp-backdrop")[0]
    assert (declared(backdrop, "overflow-y") or declared(backdrop, "overflow")) in {
        "auto",
        "scroll",
    }, "the backdrop cannot scroll, so a card taller than the viewport is stranded"


def test_popup_backdrop_has_a_scrim(style_css):
    bodies = rule_bodies(style_css, ".dp-backdrop")
    assert bodies, ".dp-backdrop rule not found in style.css"
    backgrounds = [
        declared(b, "background") or declared(b, "background-color") for b in bodies
    ]
    assert any(backgrounds), (
        "the backdrop paints nothing, so no page content is dimmed behind the popup"
    )


class _NestingProbe(HTMLParser):
    """Records whether `needle` is reached while inside an element carrying `host`.

    Asserting `position: absolute` alone is not enough: absolute resolves against
    the nearest *positioned ancestor*, so the button only tracks the card if it is
    actually inside it. It used to be a sibling, which anchored it to the fixed
    backdrop and left it floating on the scrim beside the bounded card.
    """

    def __init__(self, host, needle):
        super().__init__()
        self.host, self.needle = host, needle
        self._depth = 0
        self.nested = False

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class", "").split()
        if self._depth and self.needle in classes:
            self.nested = True
        # Only <div> moves the counter. div is never a void element, so every open
        # is matched by a close. Counting every tag desynchronises on <input> and
        # <br>, which HTMLParser reports as starts with no matching end — the
        # depth then never returns to zero and anything after the card reads as
        # nested inside it.
        if tag == "div":
            if self._depth:
                self._depth += 1
            elif self.host in classes:
                self._depth = 1

    def handle_endtag(self, tag):
        if tag == "div" and self._depth:
            self._depth -= 1


def test_popup_close_button_is_anchored_to_the_card(style_css):
    bodies = rule_bodies(style_css, ".dp-close")
    assert bodies, ".dp-close rule not found in style.css"
    assert declared(bodies[0], "position") == "absolute", (
        "the close button is still viewport-fixed and will float off the card"
    )

    probe = _NestingProbe("dp-card", "dp-close")
    probe.feed((TEMPLATE_DIR / "_discount_popup.html").read_text(encoding="utf-8"))
    assert probe.nested, (
        "the close button sits outside .dp-card, so position:absolute resolves "
        "against the fixed backdrop and pins it to the viewport corner"
    )


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


# ponytail: this WCAG maths is a second copy — batch 3 ships the same formula in
# home/test_contrast.py. Batch 4 branches off 4424064, where that file does not
# exist yet, so it cannot import it. When both batches land, delete this block and
# import from test_contrast instead.
def _srgb_channel(value):
    value /= 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_colour):
    hex_colour = hex_colour.lstrip("#")
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (0, 2, 4))
    return (
        0.2126 * _srgb_channel(r)
        + 0.7152 * _srgb_channel(g)
        + 0.0722 * _srgb_channel(b)
    )


def contrast_ratio(fg, bg):
    light, dark = sorted((relative_luminance(fg), relative_luminance(bg)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


@pytest.mark.parametrize("background", ["#ffffff", "#f9fafb"])
def test_muted_token_clears_aa_on_its_backgrounds(style_css, background):
    """--color-muted now paints text that previously just inherited. Every call site
    sits on white or the surface tint, so both have to clear 4.5:1."""
    root = rule_bodies(style_css, ":root")[0]
    alias = declared(root, "--color-muted")
    assert alias == "var(--color-text-muted)", f"unexpected --color-muted value: {alias}"
    resolved = declared(root, "--color-text-muted")
    assert contrast_ratio(resolved, background) >= 4.5, (
        f"muted text {resolved} on {background} is "
        f"{contrast_ratio(resolved, background):.2f}:1, below AA"
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
