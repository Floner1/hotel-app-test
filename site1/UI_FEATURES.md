# UI Features Documentation

## Overview

This document details all modern UI components and animations implemented in the Thien Tai Hotel Booking System. The design focuses on smooth animations, responsive layouts, and intuitive user interactions.

---

## 1. Infinite Scroll Galleries

### Implementation
Horizontal scrolling galleries inspired by modern web design patterns (reactbits.dev logo-loop).

### Technical Specifications

**Animation:**
```css
@keyframes scroll {
  0% { transform: translateX(0); }
  100% { transform: translateX(calc(-50%)); }
}
```

**Configuration:**
- **Duration:** 22 seconds (linear timing)
- **Direction:** Left to right continuous scroll
- **Performance:** Uses `will-change: transform` for optimization

**Responsive Sizing:**
- **Desktop:** 280px height, auto width
- **Mobile:** 200px height, auto width
- **Gap:** 60px (desktop), 30px (mobile)

**Hover Effects:**
- Scale: 1.1x zoom on hover
- Transition: 0.3s ease

**Visual Enhancements:**
- Gradient fade-out edges
- Border-radius: 8px
- Box-shadow: 0 4px 12px rgba(0,0,0,0.1)

### Where Used
- **about.html** - Photos section (lines 407-509)
- **home.html** - Rooms & Suites section (lines 482-536)
- **rooms.html** - Rooms & Suites section (lines 455-509)

### HTML Structure
```html
<div class="logo-loop-container" data-aos="fade-up">
  <div class="logo-loop-track">
    <div class="logo-loop-item">
      <img src="image.png" alt="Description" />
    </div>
    <!-- Duplicated items for seamless loop -->
  </div>
</div>
```

### Browser Compatibility
- ✅ Chrome/Edge (all versions)
- ✅ Firefox (all versions)
- ✅ Safari (all versions)
- ✅ Mobile browsers

---

## 2. Premium Services Cards

### Implementation
Clean card-based layout with hover animations and responsive grid system.

### Design Specifications

**Card Styling:**
- Background: White (#ffffff)
- Shadow: `shadow-sm` (Bootstrap utility)
- Border-radius: Default Bootstrap (0.25rem)
- Padding: Standard Bootstrap spacing

**Typography:**
- **Heading:** 3.5rem font-size, bold weight
- **Description:** 1.25rem font-size, #6c757d color
- Line-height: Optimized for readability

**Hover Animation:**
```css
.service-card:hover {
  transform: translateY(-10px);
  transition: transform 0.3s ease;
}
```

**Grid Layout:**
- Uses Bootstrap grid system
- Responsive columns: `col-md-6 col-lg-4`
- Auto-adjusts for mobile devices

### Where Used
- home.html (Premium Services)
- about.html (Our Services)
- contact.html (Why Choose Us)
- rooms.html (Premium Services)
- reservation.html (Booking Benefits)

### HTML Structure
```html
<section class="section services-section bg-light">
  <div class="container">
    <div class="row justify-content-center text-center mb-5">
      <div class="col-md-7">
        <h2 class="heading" style="font-size: 3.5rem !important;">Premium Services</h2>
        <p style="font-size: 1.25rem !important; color: #6c757d;">Description text</p>
      </div>
    </div>
    <div class="row">
      <div class="col-md-6 col-lg-4" data-aos="fade-up">
        <div class="media-feature text-center">
          <!-- Content -->
        </div>
      </div>
    </div>
  </div>
</section>
```

---

## 3. Great Offers Menu

### Implementation
Expandable dropdown menu system with hover-triggered expansion, displaying detailed room information.

### Technical Specifications

**Menu Structure:**
- Accordion-style expansion
- One menu item per room type
- Database-driven content via Django templates

**Animation Timing:**
- **Max-height transition:** 0.5s ease
- **Content fade-in:** 0.4s ease with 0.1s delay
- **Tab hover:** 0.3s ease

**States:**
- **Collapsed:** max-height: 0, opacity: 0
- **Expanded:** max-height: 600px, opacity: 1

**Interactive Elements:**
- Room name in menu tab
- Dropdown arrow (rotates 180° on hover)
- Hover changes tab background and padding

### Visual Design

**Menu Tab:**
- Padding: 25px 30px (20px on mobile)
- Background: White → Light gray on hover
- Font-size: 1.5rem (1.2rem on mobile)
- Arrow indicator: ▼ character

**Dropdown Content:**
- Padding: 30px (20px on mobile)
- Background: #f8f9fa
- Two-column layout (desktop)
- Single-column stack (mobile)

**Room Information:**
- Room image: Full-width, rounded corners
- Title: 2rem font-size (1.5rem on mobile)
- Description: #6c757d color, line-height 1.8
- Price: 2.5rem bold (2rem on mobile), #1a73e8 color
- CTA button: Bootstrap btn-primary

### Where Used
- **rooms.html** - Great Offers section (after hero, before Premium Services)

### HTML Structure
```html
<div class="flowing-menu-container" data-aos="fade-up">
  <div class="flowing-menu">
    <div class="menu-item" data-room-id="1">
      <div class="menu-tab">
        <span class="room-name">Room Type Name</span>
      </div>
      <div class="menu-dropdown">
        <div class="dropdown-content">
          <div class="row align-items-center">
            <div class="col-md-6">
              <img src="room-image.png" class="room-image">
            </div>
            <div class="col-md-6">
              <div class="room-info">
                <h3 class="room-title">Title</h3>
                <p class="room-description">Description</p>
                <div class="room-price">
                  <span class="price-amount">₫1,000,000</span>
                  <span class="price-label">/ PER NIGHT</span>
                </div>
                <a href="/reservation/" class="btn btn-primary">Book Now</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

### CSS Classes Reference

| Class | Purpose |
|-------|---------|
| `.flowing-menu-container` | Wrapper with overflow hidden |
| `.flowing-menu` | Main menu container with rounded corners |
| `.menu-item` | Individual room entry |
| `.menu-tab` | Clickable/hoverable tab |
| `.menu-dropdown` | Expandable content area |
| `.dropdown-content` | Inner content with fade animation |
| `.room-image` | Room photo styling |
| `.room-info` | Text content wrapper |
| `.room-price` | Price display flexbox |

---

## 4. AOS (Animate On Scroll) Integration

### Implementation
Third-party library for scroll-triggered entrance animations.

### Common Attributes
- **data-aos="fade-up"** - Fade in from bottom
- **data-aos-delay="100"** - Stagger animations (100ms increments)

### Usage Patterns
```html
<div data-aos="fade-up">Content appears on scroll</div>
<div data-aos="fade-up" data-aos-delay="100">Delayed appearance</div>
```

### Where Applied
- Section headings
- Gallery containers
- Service cards
- Form elements
- Images

---

## 5. Responsive Design Breakpoints

### Mobile Optimization

**Bootstrap Breakpoints:**
- `xs`: <576px (mobile phones)
- `sm`: ≥576px (landscape phones)
- `md`: ≥768px (tablets)
- `lg`: ≥992px (desktops)
- `xl`: ≥1200px (large desktops)

**Custom Media Queries:**

**Mobile (≤768px):**
- Gallery images: 200px height
- Gallery gaps: 30px
- Menu tabs: 20px padding
- Font sizes: Reduced by ~20%
- Single-column layouts

**Tablet (769px - 991px):**
- Maintains most desktop features
- Adjusted grid columns
- Optimized spacing

**Desktop (≥992px):**
- Full-size images (280px)
- Multi-column grids
- Maximum font sizes
- Enhanced hover effects

---

## 6. Color Palette

### Primary Colors
- **Primary Blue:** #1a73e8 (prices, CTAs, links)
- **Text Dark:** #333333 (headings, primary text)
- **Text Gray:** #6c757d (descriptions, secondary text)
- **Light Gray:** #e0e0e0 (borders, dividers)
- **Background Light:** #f8f9fa (section backgrounds, dropdowns)
- **White:** #ffffff (cards, tabs, main background)

### Hover States
- **Tab Hover:** #f8f9fa (light gray)
- **Link Hover:** #0d5fc3 (darker blue)
- **Card Shadow:** rgba(0,0,0,0.1) (subtle depth)

---

## 7. Typography System

### Font Families
- Primary: System font stack (Bootstrap default)
- Fallbacks: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif

### Font Sizes

**Headings:**
- **H1/H2 (Sections):** 3.5rem → 2.5rem (mobile)
- **H3 (Subsections):** 2rem → 1.5rem (mobile)
- **Menu Tabs:** 1.5rem → 1.2rem (mobile)

**Body Text:**
- **Descriptions:** 1.25rem → 1rem (mobile)
- **Prices:** 2.5rem → 2rem (mobile)
- **Price Labels:** 0.9rem (all devices)
- **Regular Text:** 1rem (base)

### Font Weights
- **Bold:** 700 (headings, prices)
- **Semibold:** 600 (menu tabs, room names)
- **Normal:** 400 (body text)

---

## 8. Performance Optimizations

### CSS Optimizations
- **will-change: transform** - Pre-optimizes animations
- **transform** instead of **top/left** - Hardware acceleration
- **transition** with easing - Smooth visual changes

### Image Optimizations
- Compressed images in `static/images/`
- Appropriate dimensions (not oversized)
- Modern formats preferred

### Load Order
1. Critical CSS (inline or early load)
2. Bootstrap CSS
3. Custom stylesheets
4. AOS library
5. JavaScript files (deferred)

---

## 9. Accessibility Features

### Semantic HTML
- Proper heading hierarchy (h1 → h2 → h3)
- Alt text on all images
- Descriptive link text

### Keyboard Navigation
- Focusable elements
- Tab order preservation
- Skip links available

### Color Contrast
- WCAG AA compliance
- Sufficient text contrast ratios
- Color not sole indicator

---

## 10. Browser Testing Checklist

### Tested Browsers
- ✅ Chrome 120+ (Windows/Mac)
- ✅ Firefox 120+ (Windows/Mac)
- ✅ Safari 17+ (Mac/iOS)
- ✅ Edge 120+ (Windows)
- ✅ Mobile Safari (iOS 16+)
- ✅ Chrome Mobile (Android 12+)

### Known Issues
None currently documented.

---

## 11. Future Enhancements

### Planned Features
- [ ] Dark mode toggle
- [ ] Animation pause/play controls
- [ ] Lazy loading for images
- [ ] Progressive Web App (PWA) support
- [ ] Enhanced mobile gestures
- [ ] Skeleton loading screens

### Performance Goals
- Lighthouse score: 90+
- Page load time: <2 seconds
- First Contentful Paint: <1 second

---

## 12. Component Reference Quick List

| Component | File(s) | Line Range | Key Feature |
|-----------|---------|------------|-------------|
| Infinite Scroll Photos | about.html | 407-509 | Photo gallery |
| Infinite Scroll Rooms | home.html, rooms.html | 482-536, 455-509 | Room showcase |
| Premium Services | All templates | Varies | Service cards |
| Great Offers Menu | rooms.html | After hero section | Expandable tabs |
| Hero Sections | All pages | Top of page | Full-width banners |
| Navigation | All pages | Header | Responsive navbar |

---

**Last Updated:** February 1, 2026  
**Maintained By:** Development Team  
**Version:** 2.0
