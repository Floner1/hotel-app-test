# CSP enforcement: what is left, and the three decisions blocking it

Status as of 2026-09-05. The policy is still `CONTENT_SECURITY_POLICY_REPORT_ONLY`
in `site1/site1/settings.py:373`. Flipping it today would break working admin
pages and silently remove two destructive-action guards.

## What is already done

All 14 inline `<script>` blocks across 8 templates carry
`nonce="{{ request.csp_nonce }}"`, and `script-src` declares the django-csp
`NONCE` sentinel. The sentinel is the half that is easy to miss: without it the
attribute renders and the browser still refuses the block. Three tests in
`site1/home/test_csp_nonce.py` pin the chain, including that the nonce in the
markup matches the one the response header advertises.

Nothing below is blocked on that work. It is blocked on inline `on*=` handlers,
which a nonce cannot cover at all.

## The 11 templates in scope

Eight carry inline `<script>`, seven carry inline handlers, four carry both.
The union is 11 files.

| Template | Nonced `<script>` | Inline handlers | Notes |
|---|---:|---:|---|
| `admin_reservations.html` | 1 | 18 | 11 are inside JS template literals, see Decision 3 |
| `home.html` | 2 | 13 | image-upload modal, all static markup |
| `room_dashboard.html` | 1 | 10 | room modal and condition buttons, all static |
| `manage_accounts.html` | 1 | 8 | also loads jQuery from a CDN, see Decision 2 |
| `admin_email_log.html` | 0 | 2 | outside the original 8, see Decision 1 |
| `admin_email_subscribers.html` | 0 | 2 | outside the original 8, see Decision 1 |
| `admin_email_campaigns.html` | 0 | 1 | outside the original 8, see Decision 1 |
| `base.html` | 5 | 0 | done |
| `reservation.html` | 2 | 0 | done |
| `contact.html` | 1 | 0 | done |
| `rooms.html` | 1 | 0 | done |
| **Total** | **14** | **54** | |

By event type: `onclick` 38, `onchange` 7, `onmouseover` 3, `onmouseout` 3,
`onsubmit` 2, `onkeyup` 1.

Of the 54, **43 are static** and convert mechanically. The other **11 are
injected at runtime** and all live in `admin_reservations.html`. Verified by
tracking template-literal nesting per file, not by eye.

## Decision 1: three templates sit outside the original scope

The task that started this work named 8 templates, chosen because they contain
inline `<script>`. Handlers do not follow that boundary. Three templates carry
handlers and no inline script, so they were never on the list:

- `admin_email_log.html:58,64` and `admin_email_subscribers.html:60` use
  `onchange="this.form.submit()"` on filter dropdowns. Under enforcement the
  filters stop working. Annoying, not dangerous.
- `admin_email_subscribers.html:82` and `admin_email_campaigns.html:68` use
  `onsubmit="return confirm(...)"`.

The `onsubmit` pair is the reason this cannot be deferred. When CSP blocks an
inline `onsubmit`, the handler does not run, so it cannot return `false`, so
**the form submits anyway with no confirmation**. The guards protect
unsubscribing a named subscriber and sending a campaign to every active
subscriber. Enforcing CSP without converting these makes a destructive action
one misclick away, and it fails silently.

**Decision needed:** extend scope to 11 templates. Leaving these three out does
not make the flip safer, it makes it worse than the status quo.

## Decision 2: the jQuery CDN tag

`manage_accounts.html:576` loads jQuery 3.5.1 from `https://code.jquery.com`.
`script-src 'self'` blocks it outright, no nonce helps.

The page already extends `base.html`, which loads jQuery 3.3.1 locally at
`base.html:55`. So the CDN tag is a second jQuery layered over the first, and
the page currently runs 3.5.1 rather than the vendored 3.3.1.

The page's own inline script uses jQuery zero times, so deleting line 576 is
safe for that page's code. The residual risk is that anything else running
after it on that page silently moves from 3.5.1 back to 3.3.1. jQuery 3.4/3.5
changed `htmlPrefilter` and self-closing tag parsing, so this is a real version
change even though nothing here obviously depends on it.

**Recommendation:** delete line 576 and load the page to confirm. Do not swap
the CDN URL for a local 3.5.1 copy; that adds a second vendored jQuery to
maintain in order to preserve a version nothing asked for.

## Decision 3: eleven handlers are on elements that do not exist yet

`admin_reservations.html` builds four modals as JS template literals and
injects them with `overlay.innerHTML = modalContent`, at lines 1193, 1242,
1334 and 1406. The markup inside carries inline handlers:

| Modal | Handler lines | Handlers |
|---|---|---:|
| View booking | 1171, 1188 | 2 |
| Edit booking | 1219, 1234 | 2 |
| Delete booking | 1326, 1327 | 2 |
| Add booking | 1375, 1381, 1385, 1386, 1398 | 5 |

Eleven of that file's 18 handlers. The remaining 7, at lines 492, 517, 632 and
696 to 698, are server-rendered and convert with a plain `addEventListener`.

These 11 cannot: the elements are created after page load, so a listener bound
at `DOMContentLoaded` finds nothing to bind to. Each needs either event
delegation from a stable ancestor, or listeners attached immediately after the
`innerHTML` assignment. Line 1327 is the sharpest case,
`onclick="confirmDelete(${id}, this)"` interpolates a booking id into the
markup, so a delegated handler has to recover that id from a `data-` attribute
instead of a closure.

This is a behavioural change, not a mechanical rewrite. Under enforcement today
these modals render and their buttons do nothing, including Cancel, which
leaves a full-screen overlay with no way out.

## Suggested order

1. Convert the 5 handlers in the three email-admin templates. Smallest change,
   removes the destructive-action risk, and settles Decision 1 by doing it.
2. Delete `manage_accounts.html:576` and load the page.
3. Convert the remaining 38 static handlers: 13 in `home.html`, 10 in
   `room_dashboard.html`, 8 in `manage_accounts.html`, 7 in
   `admin_reservations.html`. Mechanical, one JS file per template or one
   shared file.
4. Restructure the four modals in `admin_reservations.html`. This is the real
   work and deserves its own change and its own tests.
5. Only then rename `CONTENT_SECURITY_POLICY_REPORT_ONLY` to
   `CONTENT_SECURITY_POLICY` in `settings.py:373`.

Between step 4 and step 5, this should hold and is worth asserting in a test:

    grep -rcoE '\bon[a-z]+\s*="' site1/templates/*.html   # expect 0 everywhere

## Verification the flip needs

Report-only means the browser reports and does not block, so a clean console
today proves nothing about enforcement. After the flip, load each of the 11
templates in a browser and confirm no `Refused to execute` or
`Refused to load` entries. The four admin_reservations modals have to be opened
and dismissed, not just rendered, since their handlers only run on interaction.
