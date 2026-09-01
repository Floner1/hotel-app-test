"""WCAG 2.1 AA contrast for the text the audit measured as failing.

No axe-core in this stack and adding it would be a new dependency, so the
ratios are computed here from the sRGB relative-luminance formula in WCAG 2.1
(the same arithmetic axe runs) against the colours actually declared in the
shipped stylesheets. The declarations are parsed out of the real files rather
than restated, so editing a colour back to a failing value fails this suite.

Semi-transparent text is composited over its own background first: rgba white
at 0.28 on #1a1a1a is not white, it is the blend, and that blend is what a
reader sees.
"""

import re
from pathlib import Path

import pytest

SITE1 = Path(__file__).resolve().parent.parent
AA_NORMAL_TEXT = 4.5

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
POPUP_PANEL = (0x1A, 0x1A, 0x1A)   # .dp-left, style.css
FOOTER = BLACK                      # .site-footer, overrides.css:388


# ── WCAG 2.1 arithmetic ──


def _channel(value):
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (_channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


def composite(fg, alpha, bg):
    """Flatten a semi-transparent foreground onto an opaque background."""
    return tuple(round(f * alpha + b * (1 - alpha)) for f, b in zip(fg, bg))


# ── reading colours out of the shipped files ──


def declared_color(source, selector):
    """The `color:` value inside `selector { ... }` in `source`.

    Deliberately literal: it finds the exact selector text and the first
    `color:` in that block. A refactor that renames the selector fails here
    loudly rather than silently measuring nothing.
    """
    text = (SITE1 / source).read_text(encoding='utf-8')
    block = re.search(
        re.escape(selector) + r'\s*\{([^}]*)\}', text
    )
    assert block, f'{selector} not found in {source}'
    decl = re.search(r'(?<!-)\bcolor\s*:\s*([^;]+);', block.group(1))
    assert decl, f'no color declared for {selector} in {source}'
    return decl.group(1).strip()


def parse_color(value):
    """Return (rgb, alpha) for #rrggbb, #rgb, or rgba()/rgb()."""
    value = value.strip()
    rgba = re.match(
        r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)', value
    )
    if rgba:
        r, g, b, a = rgba.groups()
        return (int(r), int(g), int(b)), float(a) if a is not None else 1.0
    hexv = re.match(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$', value)
    assert hexv, f'unrecognised colour: {value!r}'
    h = hexv.group(1)
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)), 1.0


def effective_ratio(source, selector, background):
    rgb, alpha = parse_color(declared_color(source, selector))
    return contrast_ratio(composite(rgb, alpha, background), background)


# The newsletter input paints rgba(255,255,255,0.05) over the black footer, so
# its placeholder sits on that blend rather than on #000.
INPUT_SURFACE = composite(WHITE, 0.05, FOOTER)

FAILING_IN_THE_AUDIT = [
    ('static/css/style.css', '.dp-footnote', POPUP_PANEL, 2.52),
    ('static/css/overrides.css', '.site-footer__bottom p', FOOTER, 2.45),
    ('static/css/overrides.css', '.site-footer__newsletter-copy', FOOTER, 4.43),
    (
        'static/css/overrides.css',
        '.site-footer__newsletter-form .form-control::placeholder',
        INPUT_SURFACE,
        2.65,
    ),
    ('templates/home.html', '.bw-guests-note', WHITE, 2.54),
]


@pytest.mark.parametrize(
    'source,selector,background,measured_before',
    FAILING_IN_THE_AUDIT,
    ids=[c[1] for c in FAILING_IN_THE_AUDIT],
)
def test_audited_text_meets_aa(source, selector, background, measured_before):
    ratio = effective_ratio(source, selector, background)
    assert ratio >= AA_NORMAL_TEXT, (
        f'{selector} in {source} is {ratio:.2f}:1 against '
        f'rgb{background}, below the {AA_NORMAL_TEXT}:1 AA floor for normal '
        f'text (was {measured_before:.2f}:1 when audited)'
    )


PASSED_IN_THE_AUDIT = [
    ('static/css/overrides.css', '.site-footer__col a', FOOTER, 6.25),
    ('static/css/overrides.css', '.site-footer__address', FOOTER, 5.32),
]


@pytest.mark.parametrize(
    'source,selector,background,measured_before',
    PASSED_IN_THE_AUDIT,
    ids=[c[1] for c in PASSED_IN_THE_AUDIT],
)
def test_text_that_already_passed_still_passes(
    source, selector, background, measured_before
):
    """Guards against a blanket darkening of the footer that fixes the failures
    by moving everything, including the two that were already fine."""
    ratio = effective_ratio(source, selector, background)
    assert ratio >= AA_NORMAL_TEXT, (
        f'{selector} regressed to {ratio:.2f}:1 (was {measured_before:.2f}:1)'
    )


def test_the_ratio_maths_matches_known_values():
    """Anchors the formula itself. Black on white is exactly 21:1, and a colour
    against itself is exactly 1:1; if these drift the suite above is measuring
    nothing."""
    assert round(contrast_ratio(BLACK, WHITE), 2) == 21.0
    assert round(contrast_ratio(WHITE, WHITE), 2) == 1.0
