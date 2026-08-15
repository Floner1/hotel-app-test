(function($) {

	'use strict';

  $('.site-menu-toggle').click(function(){
    var $this = $(this);
    if ( $('body').hasClass('menu-open') ) {
      $this.removeClass('open');
      $('.js-site-navbar').fadeOut(400);
      $('body').removeClass('menu-open');
    } else {
      $this.addClass('open');
      $('.js-site-navbar').fadeIn(400);
      $('body').addClass('menu-open');
    }
  });

	
	$('nav .dropdown').hover(function(){
		var $this = $(this);
		$this.addClass('show');
		$this.find('> a').attr('aria-expanded', true);
		$this.find('.dropdown-menu').addClass('show');
	}, function(){
		var $this = $(this);
			$this.removeClass('show');
			$this.find('> a').attr('aria-expanded', false);
			$this.find('.dropdown-menu').removeClass('show');
	});



	$('#dropdown04').on('show.bs.dropdown', function () {
	});

  var siteStellar = function() {
    if ($.fn.stellar) {
      $(window).stellar({
        responsive: false,
        parallaxBackgrounds: true,
        parallaxElements: true,
        horizontalScrolling: false,
        hideDistantElements: false,
        scrollProperty: 'scroll'
      });
    }
  }
  siteStellar();

  var smoothScroll = function() {
    var $root = $('html, body');

    $('a.smoothscroll[href^="#"]').click(function () {
      $root.animate({
        scrollTop: $( $.attr(this, 'href') ).offset().top
      }, 500);
      return false;
    });
  }
  smoothScroll();

  var dateAndTime = function() {
    $('#m_date').datepicker({
      'format': 'mm/dd/yyyy',
      'autoclose': true
    });
    $('#checkin_date, #checkout_date').datepicker({
      'format': 'mm/dd/yyyy',
      'autoclose': true,
      'startDate': 'today',
      'todayHighlight': true
    });
  };
  dateAndTime();


  var windowScroll = function() {

    $(window).scroll(function(){
      var $win = $(window);
      if ($win.scrollTop() > 10) {
        $('.js-site-header').addClass('scrolled');
      } else {
        $('.js-site-header').removeClass('scrolled');
      }

    });

  };
  windowScroll();



  /**
   * Put a button into a busy state for the duration of an async action.
   *
   * The admin modal forms are injected with innerHTML after page load, so the
   * blanket $('form') submit handler in base.html — which binds once on ready —
   * never sees them. Those call sites have to opt in explicitly, which is what
   * this is for.
   *
   * Returns a restore function, or null if the button was ALREADY busy. That
   * null is the double-submit guard: a second click while a request is in
   * flight gets nothing back and bails, so it cannot fire a duplicate booking.
   */
  window.btnBusy = function(btn, busyText) {
    var $btn = $(btn);
    if (!$btn.length || $btn.prop('disabled')) return null;
    var original = $btn.html();
    $btn.prop('disabled', true).html(
      '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ' +
      (busyText || 'Working...')
    );
    return function restore() {
      $btn.prop('disabled', false).html(original);
    };
  };

  // Admin "Edit Mode" links in the navbar (desktop dropdown + mobile menu).
  //
  // Was an inline onclick= in _navbar.html, which a strict `script-src 'self'`
  // CSP blocks — nonces cover <script> blocks but never inline handlers.
  //
  // Delegated, not bound direct, for two reasons: this file runs before the
  // navbar markup is parsed, and toggleEditMode itself is defined later still
  // by admin-edit.js. By click time both exist, which is what the old
  // `typeof ... === 'function'` guard was covering for. Guard kept anyway —
  // the link only renders for admins, but admin-edit.js could fail to load.
  //
  // preventDefault only, no stopPropagation: the old inline `return false`
  // suppressed the '#' jump without stopping the bubble, and the staff-tools
  // dropdown's open/close depends on that bubble reaching document.
  $(document).on('click', '.js-edit-mode-toggle', function(e) {
    e.preventDefault();
    if (typeof window.toggleEditMode === 'function') {
      window.toggleEditMode();
    }
  });

  // Staff & Admin tools dropdown — click toggle with outside-click close
  $(document).on('click', '.staff-tools-trigger', function(e) {
    e.preventDefault();
    e.stopPropagation();
    var $dropdown = $(this).closest('.staff-tools-dropdown');
    var wasOpen = $dropdown.hasClass('open');
    $('.staff-tools-dropdown').removeClass('open');
    $('.staff-tools-trigger').attr('aria-expanded', 'false');
    if (!wasOpen) {
      $dropdown.addClass('open');
      $(this).attr('aria-expanded', 'true');
    }
  });

  $(document).on('click', '.staff-tools-menu', function(e) {
    e.stopPropagation();
  });

  $(document).on('click', function() {
    $('.staff-tools-dropdown').removeClass('open');
    $('.staff-tools-trigger').attr('aria-expanded', 'false');
  });

  $(document).on('keydown', function(e) {
    if (e.key === 'Escape') {
      $('.staff-tools-dropdown').removeClass('open');
      $('.staff-tools-trigger').attr('aria-expanded', 'false');
    }
  });

  var goToTop = function() {

    $('.js-gotop').on('click', function(event){
      
      event.preventDefault();

      $('html, body').animate({
        scrollTop: $('html').offset().top
      }, 500);
      
      return false;
    });

    $(window).scroll(function(){

      var $win = $(window);
      if ($win.scrollTop() > 200) {
        $('.js-top').addClass('active');
      } else {
        $('.js-top').removeClass('active');
      }

    });
  
  };
  goToTop();


})(jQuery);