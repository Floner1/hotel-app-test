# CLAUDE.md — hotel-app-test

Read this before touching any file in this repo.

## Scope

You may only edit frontend files: templates in `site1/templates/`, stylesheets and JS in `site1/static/`. Do not touch views, models, URLs, migrations, settings, or any backend logic unless explicitly asked.

---

## Design System

Define these tokens at the top of the main CSS file as custom properties. Every value in the codebase must reference them — no hardcoded magic numbers.

```css
:root {
  /* Colors */
  --color-primary: [MISSING: brand primary];
  --color-accent: [MISSING: brand accent];
  --color-text: #1a1a1a;
  --color-text-muted: #6b7280;
  --color-bg: #ffffff;
  --color-surface: #f9fafb;
  --color-border: #e5e7eb;

  /* Typography */
  --text-h1: 2.25rem;
  --text-h2: 1.75rem;
  --text-h3: 1.25rem;
  --text-body: 1rem;
  --text-caption: 0.875rem;
  --font-weight-heading: 600;
  --font-weight-body: 400;
  --line-height-body: 1.6;

  /* Spacing (use only these three) */
  --space-sm: 0.75rem;
  --space-md: 1.5rem;
  --space-lg: 3rem;

  /* Borders */
  --radius-sm: 4px;
  --radius-md: 8px;

  /* Motion */
  --ease: cubic-bezier(0.25, 0.1, 0.25, 1);
  --duration-fast: 150ms;
  --duration-base: 250ms;
}
```

---

## Rules — Always Follow

### Visual
- No purple gradients unless `--color-primary` is explicitly purple
- No sparkle icons, star emojis, or decorative emoji anywhere in templates
- No glowing box shadows or neon hover effects
- Hover lifts: `translateY(-4px)` max, `box-shadow` spread 8px max
- All transitions use `var(--ease)` and `var(--duration-base)` — no bare `ease` or `linear`
- Border radius must be `var(--radius-sm)` or `var(--radius-md)` everywhere — cards, buttons, inputs, all match

### Typography
- Stick to the five sizes defined above — no deviations
- No oversized headings paired with ultra-thin body weight
- No `font-size` values outside the design system

### Layout
- Component placement must be consistent across all pages
- Icon sizing must be proportional to surrounding text — no oversized standalone icons

### Animations
- Remove AOS.js entirely — delete the import, the `data-aos` attributes, and the script tag
- Replace any scroll entrance effects with a single manually-written fade-in using `var(--ease)` — or remove animations entirely
- No animations that serve decoration only

### Interactions
- Every button must have a visible active/loading state
- Every form submission must show progress feedback before the page responds
- Every toggle, tab, carousel, and dropdown must actually work — if it does not, fix it or remove it
- Add skeleton screens or a spinner to any section that loads data dynamically
- All social links and nav links must go to a real URL — remove any that go nowhere

### Copy
- No generic hero phrases: "Book your dream stay", "Experience luxury", "Create unforgettable memories", or similar
- Replace with specific, factual copy about Thien Tai Hotel
- No fake testimonials or placeholder names like "Sarah Chen"
- No AI-generated face photos used as testimonials
- Remove "Built with ❤️ by X" from the footer

---

## Rules — Never Do

- Do not add any new animations without a clear functional reason
- Do not introduce new color values outside the design system
- Do not leave non-functional UI components in place
- Do not guess at brand colors or real hotel copy — insert `[MISSING: description]` instead
- Do not use emoji in headings, buttons, or any UI element
- Do not use `ease` or `linear` as transition timing — always use `var(--ease)`

---

## How to Work

Go file by file. For each file you change:
1. State what you found
2. State what you changed and why
3. Show the updated code

Skip files with no changes. If you cannot determine a correct value, write `[MISSING: explanation]` and move on — do not guess.

---

## Stack Reference

- Django 5.2 / Python 3.x
- Bootstrap 4
- jQuery
- Templates: `site1/templates/`
- Static: `site1/static/css/`, `site1/static/js/`, `site1/static/images/`
