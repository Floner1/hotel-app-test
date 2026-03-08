/* ==========================================================================
   Admin Inline Text Editor – "Edit Mode" toggle
   Allows admin/staff users to click any text element and edit it in-place
   using a modal.  Overrides are persisted in the SiteContent table and
   loaded on every page via the text_overrides context processor.
   ========================================================================== */
(function () {
  'use strict';

  /* ---- configuration ---- */
  var TEXT_TAGS = 'h1,h2,h3,h4,h5,h6,p,span,a,button,label,li,td,th,small,em,strong,blockquote';
  var SAVE_URL = '';          // set from template
  var CSRF     = '';          // set from template
  var PAGE_ID  = '';          // set from template  (e.g. "home", "about")
  var OVERRIDES = {};         // set from template  (JSON of saved overrides)

  /* ---- state ---- */
  var editMode   = false;
  var currentEl  = null;      // element being edited
  var currentKey = '';

  /* ---- helpers ---- */
  function hashText(s) {
    /* Simple 32-bit FNV-1a – gives a short, stable fingerprint of the
       *original* (default) text so we can build a unique DB key.  */
    var h = 0x811c9dc5;
    for (var i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 0x01000193);
    }
    return ('0000000' + (h >>> 0).toString(36)).slice(-6);
  }

  function getDefaultText(el) {
    return (el.getAttribute('data-default-text') || el.textContent).trim();
  }

  function buildKey(el) {
    var tag = el.tagName.toLowerCase();
    var def = getDefaultText(el);
    return PAGE_ID + ':' + tag + ':' + hashText(def);
  }

  function isEditable(el) {
    /* Only pick elements that contain *direct* text (TextNode children)
       and are not part of the admin edit UI itself.  */
    if (el.closest('#adminEditToggle, #aeModal, #aeDbConfirm, .ae-modal, .ae-modal-box, .ae-db-confirm, .site-menu-toggle, script, style, noscript, .admin-upload-btn, .hero-admin-btn-area, .image-upload-modal')) return false;
    if (el.classList.contains('admin-edit-toggle-btn') || el.id === 'adminEditToggle') return false;
    // Must have some direct text
    var text = '';
    for (var i = 0; i < el.childNodes.length; i++) {
      if (el.childNodes[i].nodeType === 3) text += el.childNodes[i].nodeValue;
    }
    return text.trim().length > 0;
  }

  /* ---- apply saved overrides on page load ---- */
  function applyOverrides() {
    if (!OVERRIDES || !Object.keys(OVERRIDES).length) return;
    var els = document.querySelectorAll(TEXT_TAGS);
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (!isEditable(el)) continue;
      // Store the original default text BEFORE we override
      if (!el.hasAttribute('data-default-text')) {
        el.setAttribute('data-default-text', el.textContent.trim());
      }
      var key = buildKey(el);
      if (OVERRIDES[key] !== undefined) {
        // Replace only the direct text nodes, keep child elements
        setDirectText(el, OVERRIDES[key]);
      }
    }
  }

  function setDirectText(el, newText) {
    /* Replace only the first TEXT_NODE child (keeps nested elements intact). */
    for (var i = 0; i < el.childNodes.length; i++) {
      if (el.childNodes[i].nodeType === 3 && el.childNodes[i].nodeValue.trim().length > 0) {
        el.childNodes[i].nodeValue = newText;
        return;
      }
    }
    // fallback: if no existing text node, prepend one
    el.insertBefore(document.createTextNode(newText), el.firstChild);
  }

  function getDirectText(el) {
    for (var i = 0; i < el.childNodes.length; i++) {
      if (el.childNodes[i].nodeType === 3 && el.childNodes[i].nodeValue.trim().length > 0) {
        return el.childNodes[i].nodeValue.trim();
      }
    }
    return el.textContent.trim();
  }

  /* ---- edit-mode hover highlight ---- */
  function onMouseOver(e) {
    if (!editMode) return;
    var el = e.target.closest(TEXT_TAGS);
    if (el && isEditable(el)) {
      el.classList.add('ae-highlight');
    }
  }
  function onMouseOut(e) {
    if (!editMode) return;
    var el = e.target.closest(TEXT_TAGS);
    if (el) el.classList.remove('ae-highlight');
  }

  /* ---- click → open modal ---- */
  function onClick(e) {
    if (!editMode) return;
    var el = e.target.closest(TEXT_TAGS);
    if (!el || !isEditable(el)) return;
    e.preventDefault();
    e.stopPropagation();

    currentEl  = el;
    if (!el.hasAttribute('data-default-text')) {
      el.setAttribute('data-default-text', el.textContent.trim());
    }
    currentKey = buildKey(el);

    // Check if this element is database-sourced (has data-ct-key)
    var ctKey = el.getAttribute('data-ct-key');
    if (ctKey) {
      showDbConfirm(ctKey, el);
    } else {
      openEditModal();
    }
  }

  /* ---- DB confirmation modal ---- */
  function showDbConfirm(ctKey, el) {
    var overlay = document.getElementById('aeDbConfirm');
    var keySpan = document.getElementById('aeDbKeyName');
    keySpan.textContent = ctKey;
    overlay.classList.add('ae-show');
  }

  function closeDbConfirm() {
    document.getElementById('aeDbConfirm').classList.remove('ae-show');
  }

  function confirmDbEdit() {
    closeDbConfirm();
    openEditModal();
  }

  function cancelDbEdit() {
    closeDbConfirm();
    currentEl  = null;
    currentKey = '';
  }

  /* ---- open the text edit modal ---- */
  function openEditModal() {
    var ta  = document.getElementById('aeTextarea');
    ta.value = getDirectText(currentEl);
    document.getElementById('aeModal').classList.add('ae-show');
    ta.focus();
    ta.select();
    document.getElementById('aeSaveBtn').disabled = false;
    document.getElementById('aeSaveBtn').textContent = 'Save';
  }

  /* ---- save ---- */
  function save() {
    var newValue = document.getElementById('aeTextarea').value.trim();
    if (!newValue || !currentKey) return;
    var btn = document.getElementById('aeSaveBtn');
    btn.disabled = true;
    btn.textContent = 'Saving\u2026';

    // Build payload — include db_key if the element is database-sourced
    var payload = { key: currentKey, value: newValue };
    if (currentEl && currentEl.getAttribute('data-ct-key')) {
      payload.db_key = currentEl.getAttribute('data-ct-key');
    }

    fetch(SAVE_URL, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body:    JSON.stringify(payload)
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.status === 'success') {
        setDirectText(currentEl, data.value);
        OVERRIDES[currentKey] = data.value;
        showToast('Text updated!', false);
        closeModal();
      } else {
        showToast(data.message || 'Save failed', true);
        btn.disabled = false;
        btn.textContent = 'Save';
      }
    })
    .catch(function () {
      showToast('Save failed', true);
      btn.disabled = false;
      btn.textContent = 'Save';
    });
  }

  /* ---- modal helpers ---- */
  function closeModal() {
    document.getElementById('aeModal').classList.remove('ae-show');
    currentEl  = null;
    currentKey = '';
  }

  /* ---- toast (reuse page-level showToast if it exists) ---- */
  function showToast(msg, isError) {
    if (typeof window.showToast === 'function') {
      window.showToast(msg, isError);
      return;
    }
    // fallback mini-toast
    var t = document.createElement('div');
    t.textContent = msg;
    t.style.cssText = 'position:fixed;bottom:30px;left:50%;transform:translateX(-50%);background:'
      + (isError ? '#dc3545' : '#28a745') + ';color:#fff;padding:12px 24px;border-radius:8px;'
      + 'z-index:99999;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,.2);transition:opacity .4s';
    document.body.appendChild(t);
    setTimeout(function () { t.style.opacity = '0'; }, 2500);
    setTimeout(function () { t.remove(); }, 3000);
  }

  /* ---- toggle button ---- */
  function toggleEditMode() {
    editMode = !editMode;
    var btn = document.getElementById('adminEditToggle');
    if (editMode) {
      btn.textContent = '✕ Exit Edit Mode';
      btn.classList.add('ae-active');
      document.body.classList.add('ae-editing');
    } else {
      btn.textContent = '✎ Edit Mode';
      btn.classList.remove('ae-active');
      document.body.classList.remove('ae-editing');
      // remove any lingering highlight
      document.querySelectorAll('.ae-highlight').forEach(function (el) {
        el.classList.remove('ae-highlight');
      });
    }
  }

  /* ---- build the UI (toggle button + modal) ---- */
  function buildUI() {
    // Toggle button
    var btn = document.createElement('button');
    btn.id = 'adminEditToggle';
    btn.className = 'admin-edit-toggle-btn';
    btn.textContent = '✎ Edit Mode';
    btn.addEventListener('click', toggleEditMode);
    document.body.appendChild(btn);

    // Modal
    var modal = document.createElement('div');
    modal.id = 'aeModal';
    modal.className = 'ae-modal';
    modal.innerHTML =
      '<div class="ae-modal-box">' +
        '<div class="ae-modal-title">Edit text</div>' +
        '<textarea id="aeTextarea" rows="5"></textarea>' +
        '<div class="ae-modal-actions">' +
          '<button class="ae-modal-cancel" id="aeCancelBtn">Cancel</button>' +
          '<button class="ae-modal-save"   id="aeSaveBtn">Save</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(modal);

    // DB confirmation modal
    var dbConfirm = document.createElement('div');
    dbConfirm.id = 'aeDbConfirm';
    dbConfirm.className = 'ae-db-confirm';
    dbConfirm.innerHTML =
      '<div class="ae-db-confirm-box">' +
        '<div class="ae-db-confirm-icon">⚠️</div>' +
        '<div class="ae-db-confirm-title">Database Content</div>' +
        '<p class="ae-db-confirm-msg">This text is pulled from the database ' +
          '(key: <strong id="aeDbKeyName"></strong>).<br>' +
          'Editing it will update the database record directly.</p>' +
        '<div class="ae-db-confirm-actions">' +
          '<button class="ae-modal-cancel" id="aeDbCancelBtn">Cancel</button>' +
          '<button class="ae-modal-save"   id="aeDbConfirmBtn">Yes, Edit</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(dbConfirm);

    // events
    modal.addEventListener('click', function (e) { if (e.target === modal) closeModal(); });
    document.getElementById('aeCancelBtn').addEventListener('click', closeModal);
    document.getElementById('aeSaveBtn').addEventListener('click', save);
    dbConfirm.addEventListener('click', function (e) { if (e.target === dbConfirm) cancelDbEdit(); });
    document.getElementById('aeDbCancelBtn').addEventListener('click', cancelDbEdit);
    document.getElementById('aeDbConfirmBtn').addEventListener('click', confirmDbEdit);

    // Escape to close modal or exit edit mode
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        if (document.getElementById('aeDbConfirm').classList.contains('ae-show')) {
          cancelDbEdit();
        } else if (document.getElementById('aeModal').classList.contains('ae-show')) {
          closeModal();
        } else if (editMode) {
          toggleEditMode();
        }
      }
    });

    // hover & click
    document.addEventListener('mouseover', onMouseOver, true);
    document.addEventListener('mouseout',  onMouseOut,  true);
    document.addEventListener('click',     onClick,     true);
  }

  /* ---- public init (called from template) ---- */
  window.AdminEdit = {
    init: function (opts) {
      SAVE_URL  = opts.saveUrl  || '';
      CSRF      = opts.csrf     || '';
      PAGE_ID   = opts.pageId   || 'page';
      OVERRIDES = opts.overrides || {};

      // Apply saved overrides immediately (before user does anything)
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
          applyOverrides();
          if (opts.isAdmin) buildUI();
        });
      } else {
        applyOverrides();
        if (opts.isAdmin) buildUI();
      }
    }
  };
})();
