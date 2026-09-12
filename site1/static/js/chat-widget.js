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
    // May be empty: get_hotel_info() falls back to settings.HOTEL_DEFAULT_PHONE,
    // and the context processor hands back hotel=None if its query raises.
    var phone = $.trim(String($widget.data('phone') || ''));
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

    // Staged words, not a ticking clock. A counter climbing past 60 turns the
    // wait into a stopwatch on something broken, which is the impression this
    // exists to remove. Measured median is about 12s and the tail runs past
    // 60s, so the stages are placed to change once during a normal wait and
    // again well into a long one: a guest who sees the words move knows the
    // thing is alive.
    var WAIT_STAGES = [
      [0,  'Looking that up'],
      [12, 'Still working on that'],
      [35, 'Thanks for waiting, nearly there']
    ];

    var waitTimer = null;
    var waitStartedAt = 0;
    var lastWaitLabel = null;

    // Writes only when the wording actually changes. The label sits inside
    // #tt-chat-log, which is role="log" aria-live="polite", so replacing its
    // text node is an announcement. Rewriting the same sentence every second
    // would read it out every second for the length of the wait.
    function tickWait() {
      var elapsed = (Date.now() - waitStartedAt) / 1000;
      var label = WAIT_STAGES[0][1];
      for (var i = 0; i < WAIT_STAGES.length; i++) {
        if (elapsed >= WAIT_STAGES[i][0]) label = WAIT_STAGES[i][1];
      }
      if (label !== lastWaitLabel) {
        lastWaitLabel = label;
        $('#tt-chat-typing .tt-chat__typing-label').text(label);
        // Later stages are longer strings. If one wraps, the bubble grows and
        // the newest line drops below the fold on a short panel.
        scrollToEnd();
      }
    }

    function showTyping() {
      // The dots move into their own wrapper so the label is not caught by the
      // nth-child rules that stagger them.
      $('<div class="tt-chat__msg tt-chat__msg--bot tt-chat__typing" id="tt-chat-typing">' +
        '<span class="tt-chat__typing-label"></span>' +
        '<span class="tt-chat__typing-dots" aria-hidden="true">' +
        '<span></span><span></span><span></span></span></div>').appendTo($log);
      waitStartedAt = Date.now();
      lastWaitLabel = null;
      tickWait();
      waitTimer = setInterval(tickWait, 1000);
      scrollToEnd();
    }

    function clearTyping() {
      // Both the success and the error route come through here, so this is the
      // only teardown the timer needs. Missing it would leave one interval per
      // message running for the life of the page.
      clearInterval(waitTimer);
      waitTimer = null;
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
        // $.ajax defaults to no timeout, which meant a slow model held the
        // browser for as long as the socket stayed open. The server's own
        // worst case is longer than anyone will sit through: the view holds
        // one model slot across both attempts, so 2 x REQUEST_TIMEOUT_SECONDS
        // is 350s before it answers at all.
        //
        // 111s is derived, not picked. It is what the server can legitimately
        // spend on ONE attempt: NUM_PREDICT (2400) tokens at the same
        // pessimistic 25 tok/s floor REQUEST_TIMEOUT_SECONDS is built from,
        // plus its same 15s of overhead. Past that point the retry is running,
        // which means the first attempt already came back empty.
        //
        // The earlier 60s sat UNDER the slowest round trip anyone has measured
        // (88.5s, 2026-09-12 audit), so it was cutting off replies that were
        // on their way and telling the guest to try again, which spends the
        // one model slot twice on the same question. Raise NUM_PREDICT and
        // this has to move with it; the test pins that relationship.
        timeout: 111000,
        success: function (data) {
          clearTyping();
          if (data.status === 'ok') {
            addMessage(data.reply, 'bot');
          } else {
            addMessage(data.message || 'Something went wrong.', 'error');
          }
        },
        error: function (xhr, textStatus) {
          clearTyping();
          var msg = (xhr.responseJSON && xhr.responseJSON.message)
            ? xhr.responseJSON.message
            : 'Something went wrong. Please try again.';
          // A timeout has no response body, so the line above left the guest
          // with the generic "something went wrong" and no idea whether
          // retrying was worth it. Say what happened and what to do.
          if (textStatus === 'timeout') {
            // "Call the hotel" with no number is not an action. Every other
            // handoff here names one: the session-limit 429 gets it from the
            // hotel row server-side. A client timeout has no response body, so
            // this one reads it off the page instead.
            msg = 'That is taking longer than it should.';
            msg += phone
              ? ' Please try again, or call us on ' + phone + ' for an answer now.'
              : ' Please try again in a moment.';
          } else if (xhr.status === 429) {
            var wait = parseInt(xhr.getResponseHeader('Retry-After'), 10);
            if (wait > 0) {
              msg = 'Too many messages. Please wait ' + wait +
                (wait === 1 ? ' second' : ' seconds') + ' and try again.';
            }
          }
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
