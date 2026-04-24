  const GAS_WEB_APP_URL = 'https://script.google.com/macros/s/AKfycbzN9ViDkdRJ6Uj-KCjqbB1YxLL0AKg9LjrYyp5AtoL7qsTiUdm-un6vrYRntvG71Rt0mw/exec';

  // Fade-in on scroll
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) entry.target.classList.add('visible');
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

  // Hamburger menu
  const hamburger = document.getElementById('hamburger');
  const nav = document.getElementById('header-nav');
  if (hamburger && nav) {
    hamburger.addEventListener('click', function() {
      hamburger.classList.toggle('active');
      nav.classList.toggle('open');
    });
    nav.querySelectorAll('a').forEach(function(link) {
      link.addEventListener('click', function() {
        hamburger.classList.remove('active');
        nav.classList.remove('open');
      });
    });
  }

  // Case carousel
  document.querySelectorAll('.case-carousel').forEach(function(carousel) {
    var slides = Array.from(carousel.querySelectorAll('.case-slide'));
    if (!slides.length) return;

    var title = carousel.querySelector('.case-carousel-title');
    var current = carousel.querySelector('.case-carousel-current');
    var total = carousel.querySelector('.case-carousel-total');
    var prev = carousel.querySelector('.case-carousel-prev');
    var next = carousel.querySelector('.case-carousel-next');
    var activeIndex = slides.findIndex(function(slide) {
      return slide.classList.contains('is-active');
    });

    if (activeIndex < 0) activeIndex = 0;
    if (total) total.textContent = String(slides.length);

    function renderCase(index) {
      activeIndex = (index + slides.length) % slides.length;

      slides.forEach(function(slide, slideIndex) {
        var isActive = slideIndex === activeIndex;
        slide.classList.toggle('is-active', isActive);
        slide.hidden = !isActive;
        slide.setAttribute('aria-hidden', String(!isActive));
      });

      if (title) {
        title.textContent = slides[activeIndex].dataset.caseTitle || '';
      }

      if (current) {
        current.textContent = String(activeIndex + 1);
      }
    }

    if (prev) {
      prev.addEventListener('click', function() {
        renderCase(activeIndex - 1);
      });
    }

    if (next) {
      next.addEventListener('click', function() {
        renderCase(activeIndex + 1);
      });
    }

    renderCase(activeIndex);
  });

  // FAQ accordion
  document.querySelectorAll('.faq-q').forEach(function(q) {
    q.addEventListener('click', function() {
      var item = q.parentElement;
      var isOpen = item.classList.contains('faq-open');
      document.querySelectorAll('.faq-item').forEach(function(el) {
        el.classList.remove('faq-open');
      });
      if (!isOpen) item.classList.add('faq-open');
    });
  });

  function parseGasResponse(response) {
    return response.text().then(function(text) {
      if (!text) return { result: response.ok ? 'success' : 'error' };

      try {
        return JSON.parse(text);
      } catch (error) {
        return { result: response.ok ? 'success' : 'error', message: text };
      }
    });
  }

  function renderFormMessage(form, className, message) {
    form.innerHTML = '<p class="' + className + '">' + message + '</p>';
  }

  function bindGasForm(form, options) {
    if (!form) return;

    var submitButton = form.querySelector(options.submitSelector);
    if (!submitButton) return;

    var initialLabel = submitButton.textContent;

    form.addEventListener('submit', function(e) {
      e.preventDefault();

      submitButton.textContent = options.loadingLabel;
      submitButton.disabled = true;

      fetch(GAS_WEB_APP_URL, {
        method: 'POST',
        body: new FormData(form)
      })
      .then(parseGasResponse)
      .then(function(payload) {
        if (payload && payload.result === 'error') {
          throw new Error(payload.message || options.errorMessage);
        }

        if (options.validateSuccess && !options.validateSuccess(payload)) {
          throw new Error(options.errorMessage);
        }

        renderFormMessage(
          form,
          options.successClass,
          (payload && payload.message) || options.successMessage
        );
      })
      .catch(function() {
        submitButton.textContent = initialLabel;
        submitButton.disabled = false;

        if (options.inlineError) {
          var feedback = form.querySelector('.newsletter-feedback');
          if (!feedback) {
            feedback = document.createElement('p');
            feedback.className = 'newsletter-feedback is-error';
            form.appendChild(feedback);
          }
          feedback.textContent = options.errorMessage;
          return;
        }

        alert(options.errorMessage);
      });
    });
  }

  // Contact form submission
  const form = document.getElementById('contact-form');
  if (form) {
    bindGasForm(form, {
      submitSelector: '.form-submit',
      loadingLabel: '送信中...',
      successClass: 'form-success',
      successMessage: '送信が完了しました。<br>1営業日以内にご返信いたします。',
      errorMessage: '送信に失敗しました。時間をおいて再度お試しください。',
      validateSuccess: function(payload) {
        return !payload || !payload.formType || payload.formType === 'contact';
      },
      inlineError: false
    });
  }

  document.querySelectorAll('.newsletter-form').forEach(function(newsletterForm) {
    bindGasForm(newsletterForm, {
      submitSelector: '.newsletter-submit',
      loadingLabel: '登録中...',
      successClass: 'newsletter-feedback is-success',
      successMessage: '確認メールを送信しました。メール内のリンクを押すと登録が完了します。',
      errorMessage: '登録に失敗しました。時間をおいて再度お試しください。',
      validateSuccess: function(payload) {
        return !!(
          payload &&
          payload.result === 'success' &&
          payload.formType === 'newsletter' &&
          payload.message
        );
      },
      inlineError: true
    });
  });
