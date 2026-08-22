/* Front desk chat widget.
 *
 * Open/close is a class toggle — CSS owns the motion. That is deliberate:
 * a CSS transition interpolates from the element's *current* computed value,
 * so clicking the bubble mid-animation reverses from wherever the panel
 * actually is instead of snapping to the end state first. State flips on the
 * click itself, never on transitionend, so the widget can always be caught
 * and sent back the other way.
 *
 * The AJAX call copies the newsletter signup in base.html verbatim: POST,
 * X-Requested-With header, and csrfmiddlewaretoken in the form body. No new
 * CSRF mechanism.
 */
(function ($) {
  'use strict';

  $(function () {
    var $widget = $('#tt-chat');
    if (!$widget.length) return;

    var $bubble = $('#tt-chat-bubble');
    var $panel = $('#tt-chat-panel');
    var $log = $('#tt-chat-log');
    var $form = $('#tt-chat-form');
    var $input = $('#tt-chat-input');
    var $send = $('#tt-chat-send');

    var url = $widget.data('chat-url');
    var csrf = $widget.data('csrf');
    var pending = false;

    function isOpen() {
      return $widget.hasClass('is-open');
    }

    function open() {
      $widget.addClass('is-open');
      $bubble.attr('aria-expanded', 'true').attr('aria-label', 'Close chat with the front desk');
      $panel.attr('aria-hidden', 'false');
      scrollToEnd();
      // Focus after the panel is actually visible, or the browser refuses it.
      setTimeout(function () { $input.trigger('focus'); }, 60);
    }

    function close() {
      $widget.removeClass('is-open');
      $bubble.attr('aria-expanded', 'false').attr('aria-label', 'Open chat with the front desk');
      $panel.attr('aria-hidden', 'true');
    }

    function toggle() {
      if (isOpen()) {
        close();
        $bubble.trigger('focus');
      } else {
        open();
      }
    }

    function scrollToEnd() {
      $log.scrollTop($log[0].scrollHeight);
    }

    // .text() escapes — guest input and model output both land as text,
    // never as markup.
    function addMessage(text, kind) {
      $('<div>')
        .addClass('tt-chat__msg tt-chat__msg--' + kind)
        .text(text)
        .appendTo($log);
      scrollToEnd();
    }

    function showTyping() {
      $('<div class="tt-chat__msg tt-chat__msg--bot tt-chat__typing" id="tt-chat-typing">' +
        '<span></span><span></span><span></span></div>').appendTo($log);
      scrollToEnd();
    }

    function clearTyping() {
      $('#tt-chat-typing').remove();
    }

    function setPending(state) {
      pending = state;
      $send.prop('disabled', state);
    }

    // ---- open / close ----
    $bubble.on('click', toggle);
    $('#tt-chat-close').on('click', function () {
      close();
      $bubble.trigger('focus');
    });

    $(document).on('keydown', function (e) {
      // Escape closes the chat, but only if the newsletter popup is not up —
      // that one owns Escape while it is open.
      if (e.key === 'Escape' && isOpen() && !$('body').hasClass('dp-open')) {
        close();
        $bubble.trigger('focus');
      }
    });

    // ---- composing ----
    // Enter sends, Shift+Enter makes a new line.
    $input.on('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        $form.trigger('submit');
      }
    });

    // Grow the box with the text, up to the CSS max-height.
    $input.on('input', function () {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 96) + 'px';
    });

    // ---- send ----
    $form.on('submit', function (e) {
      e.preventDefault();
      if (pending) return;

      var message = $input.val().trim();
      if (!message) return;

      addMessage(message, 'user');
      $input.val('').css('height', 'auto');
      setPending(true);
      showTyping();

      $.ajax({
        url: url,
        type: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        data: { message: message, csrfmiddlewaretoken: csrf },
        success: function (data) {
          clearTyping();
          if (data.status === 'ok') {
            addMessage(data.reply, 'bot');
          } else {
            addMessage(data.message || 'Something went wrong.', 'error');
          }
        },
        error: function (xhr) {
          clearTyping();
          var msg = (xhr.responseJSON && xhr.responseJSON.message)
            ? xhr.responseJSON.message
            : 'Something went wrong. Please try again.';
          addMessage(msg, 'error');
        },
        complete: function () {
          setPending(false);
          if (isOpen()) $input.trigger('focus');
        }
      });
    });
  });
})(jQuery);
