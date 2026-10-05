/* mrpatel.com — shared behaviour: analytics layer. Case study scroll scenes are pure CSS (site.css). */
(function () {
  'use strict';

  document.documentElement.classList.add('js');

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var FADE_MS = reduceMotion ? 0 : 400; // MBTJ duration-hover on ease (expo.out)
  // Stacked layout: no pins, so no scroll-driven fades. Keep in sync with the small-screen query in site.css.
  var SMALL_SCREEN = window.matchMedia('(max-width: 699px), (max-height: 520px) and (orientation: landscape)');

  /* ---------- Start at the top on refresh ----------
     Browsers restore the last scroll position (and jump to any #hash) on reload,
     which skips the scroll-driven scenes. On a reload, start from the top instead;
     back/forward navigation keeps the browser's normal restore. */
  var navEntry = (performance.getEntriesByType && performance.getEntriesByType('navigation')[0]) || {};
  if (navEntry.type === 'reload' && 'scrollRestoration' in history) {
    history.scrollRestoration = 'manual';
    if (location.hash) history.replaceState(null, '', location.pathname + location.search);
    window.scrollTo(0, 0);
    window.addEventListener('load', function () { window.scrollTo(0, 0); });
  }

  /* ---------- Analytics: one vendor-neutral layer ----------
     Every event goes through track(). Sent to PostHog when it is loaded (live domain only,
     see partials/head.html); always queued on window.dataLayer, logged locally. */
  window.dataLayer = window.dataLayer || [];
  var page = document.body.dataset.page || location.pathname;
  var summaryOf = document.body.dataset.summaryOf;

  function track(event, props) {
    var base = { page: page };
    if (summaryOf) { base.case_study = summaryOf; base.view = 'summary'; } // summaries share the case_study value of their full study
    var payload = Object.assign(base, props || {});
    window.dataLayer.push({ event: event, props: payload, ts: Date.now() });
    // PostHog records its own $pageview, so page_view stays local to avoid double counting.
    if (event !== 'page_view' && window.posthog && typeof window.posthog.capture === 'function') {
      window.posthog.capture(event, payload);
    }
    if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
      console.debug('[track]', event, payload);
    }
  }
  window.track = track;

  track('page_view', { title: document.title, referrer: document.referrer || null });

  var caseStudy = document.body.dataset.caseStudy;
  if (caseStudy) track('case_study_open', { case_study: caseStudy });
  if (summaryOf) track('case_study_summary_open', { case_study: summaryOf });

  // Section views: fire once per section when half of it (or half the viewport) is seen.
  var seen = {};
  if ('IntersectionObserver' in window) {
    var sectionObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var id = e.target.dataset.section;
        if (!e.isIntersecting || seen[id]) return;
        if (!caseStudy) return; // footer-only pages: no section views
        var visible = e.intersectionRect.height;
        if (visible / e.boundingClientRect.height >= 0.5 || visible / window.innerHeight >= 0.5) {
          seen[id] = true;
          track('case_study_section_view', { case_study: caseStudy || null, section: id });
        }
      });
    }, { threshold: [0, 0.25, 0.5, 0.75, 1] });
    document.querySelectorAll('[data-section]').forEach(function (el) { sectionObs.observe(el); });
  }

  // Scroll depth: 25 / 50 / 75 / 100%.
  var depthMarks = [25, 50, 75, 100], depthSent = {};
  function onScroll() {
    var max = document.documentElement.scrollHeight - window.innerHeight;
    var pct = max > 0 ? Math.round((window.scrollY / max) * 100) : 100;
    depthMarks.forEach(function (m) {
      if (pct >= m && !depthSent[m]) { depthSent[m] = true; track('scroll_depth', { percent: m }); }
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });

  // Engaged time: counts only while the tab is visible and the visitor has interacted in the last 30s.
  var engagedMs = 0, lastActive = Date.now(), lastTick = Date.now();
  ['scroll', 'mousemove', 'keydown', 'touchstart', 'click'].forEach(function (t) {
    window.addEventListener(t, function () { lastActive = Date.now(); }, { passive: true });
  });
  setInterval(function () {
    var now = Date.now();
    if (document.visibilityState === 'visible' && now - lastActive < 30000) engagedMs += now - lastTick;
    lastTick = now;
  }, 1000);
  function sendEngaged() {
    if (engagedMs < 1000) return;
    track('engaged_time', { seconds: Math.round(engagedMs / 1000), case_study: caseStudy || summaryOf || null });
    engagedMs = 0;
  }
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') sendEngaged(); });
  window.addEventListener('pagehide', sendEngaged);

  // Clicks: anything with data-track sends that event name with its data-track-* props.
  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-track]');
    if (!el) return;
    var props = { label: el.textContent.trim().replace(/\s+/g, ' '), href: el.getAttribute('href') };
    Object.keys(el.dataset).forEach(function (k) {
      if (k.indexOf('track') === 0 && k !== 'track') props[k.slice(5).toLowerCase()] = el.dataset[k];
    });
    track(el.dataset.track, props);
  });

  /* ---------- Key challenges: fade stages in and out on the spot ----------
     Scenes are CSS sticky; this only decides when a block has finished its hold
     (the last --exit of its pinned distance) and fades it out in place. */
  var leaving = document.querySelectorAll('.cs-challenges .scene');
  if (leaving.length) {
    var navEl = document.querySelector('.site-nav');
    var ticking = false;
    function updateLeaving() {
      ticking = false;
      if (SMALL_SCREEN.matches) {
        document.querySelectorAll('.cs-challenges .is-leaving, .cs-challenges .is-in').forEach(function (el) {
          el.classList.remove('is-leaving', 'is-in');
        });
        return;
      }
      var nav = navEl ? navEl.offsetHeight : 0;
      var avail = window.innerHeight - nav;
      var exit = avail * 0.25; // matches --exit in site.css
      leaving.forEach(function (scene, i) {
        var r = scene.getBoundingClientRect();
        var isFinal = i === leaving.length - 1;    // final block: no fade, it scrolls out with the title
        var s = nav - r.top;                       // distance scrolled since the block pinned
        var end = r.height - avail;                // where it would start scrolling out
        scene.classList.toggle('is-leaving', !isFinal && s >= end - exit);
        scene.classList.toggle('is-in', s >= 0);   // pinned: later stages fade in on the spot
      });
      document.querySelectorAll('.cs-challenges .topic').forEach(function (topic) {
        var scenes = topic.querySelectorAll('.scene');
        topic.classList.toggle('is-leaving', scenes[scenes.length - 1].classList.contains('is-leaving'));
      });
    }
    function requestUpdate() {
      if (document.visibilityState === 'hidden') { updateLeaving(); return; } // rAF pauses in hidden tabs
      if (!ticking) { ticking = true; requestAnimationFrame(updateLeaving); }
    }
    // Paragraphs pin below each topic's subtitle; measure it (--sub-h) so a subtitle that
    // wraps to more lines on narrower screens never covers its paragraph.
    function measureSubtitles() {
      document.querySelectorAll('.cs-challenges .topic').forEach(function (topic) {
        var sub = topic.querySelector('.topic__subtitle');
        if (!sub) return;
        var pad = parseFloat(getComputedStyle(sub).paddingBottom) || 0;
        topic.style.setProperty('--sub-h', (sub.getBoundingClientRect().height - pad) + 'px');
      });
    }
    window.addEventListener('scroll', requestUpdate, { passive: true });
    window.addEventListener('resize', function () { measureSubtitles(); requestUpdate(); });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { measureSubtitles(); requestUpdate(); });
    measureSubtitles();
    updateLeaving();
  }
  /* ---------- Reading progress (case studies only) ----------
     0% at the top of the page, 100% when the bottom of the element marked
     [data-progress-end] (the Impact panel) reaches the bottom of the viewport. */
  var endEl = caseStudy && document.querySelector('[data-progress-end]');
  var navBar = document.querySelector('.site-nav');
  if (endEl && navBar) {
    var wrap = document.createElement('div');
    wrap.className = 'reading-progress';
    wrap.setAttribute('aria-hidden', 'true');
    wrap.innerHTML = '<span class="reading-progress__bar"></span>';
    navBar.appendChild(wrap);
    var bar = wrap.firstChild, progTicking = false;
    function updateProgress() {
      progTicking = false;
      var endY = endEl.getBoundingClientRect().bottom + window.scrollY - window.innerHeight;
      var p = endY > 0 ? Math.min(1, Math.max(0, window.scrollY / endY)) : 1;
      bar.style.transform = 'scaleX(' + p.toFixed(4) + ')';
    }
    function requestProgress() {
      if (document.visibilityState === 'hidden') { updateProgress(); return; }
      if (!progTicking) { progTicking = true; requestAnimationFrame(updateProgress); }
    }
    window.addEventListener('scroll', requestProgress, { passive: true });
    window.addEventListener('resize', requestProgress);
    window.addEventListener('load', requestProgress);
    updateProgress();
  }
  /* ---------- Contact: scroll to the footer without adding #contact to the URL ---------- */
  document.querySelectorAll('a[href="#contact"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var target = document.getElementById('contact');
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
    });
  });
  /* ---------- Accordion (x-accordion) ----------
     Markup ships open (aria-expanded="true") so content survives without JS. Here every panel
     closes, collapsed panels become inert (no focus, hidden from assistive tech), and the
     "Expand all" button appears and flips to "Collapse all" once every panel is open. */
  document.querySelectorAll('[data-accordion]').forEach(function (acc) {
    var items = Array.prototype.slice.call(acc.querySelectorAll('.accordion__item'));
    var all = acc.querySelector('.accordion__all');
    function set(item, open) {
      item.classList.toggle('is-open', open);
      item.querySelector('.accordion__trigger').setAttribute('aria-expanded', open ? 'true' : 'false');
      item.querySelector('.accordion__panel').inert = !open;
      var label = item.querySelector('.accordion__more-label');
      if (label) label.textContent = open ? 'Read less' : 'Read more';
    }
    function syncAll() {
      if (all) all.textContent = items.every(function (i) { return i.classList.contains('is-open'); }) ? 'Collapse all' : 'Expand all';
    }
    items.forEach(function (item) {
      set(item, false);
      item.querySelector('.accordion__trigger').addEventListener('click', function () {
        set(item, !item.classList.contains('is-open'));
        this.dataset.trackAction = item.classList.contains('is-open') ? 'open' : 'close'; // read by the click tracker after this runs
        syncAll();
      });
    });
    if (all) {
      all.hidden = false;
      all.addEventListener('click', function () {
        var open = !items.every(function (i) { return i.classList.contains('is-open'); });
        items.forEach(function (i) { set(i, open); });
        all.dataset.trackAction = open ? 'expand' : 'collapse'; // read by the click tracker after this runs
        syncAll();
      });
    }
    acc.classList.add('is-ready');
    requestAnimationFrame(function () { requestAnimationFrame(function () { acc.classList.add('is-animated'); }); });
  });

  /* ---------- Impact metrics count up ----------
     When a metric comes into view it counts quickly from 0 to its value (1s, expo.out),
     keeping its format (thousands separator, decimals). Once per visit; reduced motion shows
     the final value. aria-label always carries the final value. */
  var counters = document.querySelectorAll('[data-count-to]');
  if (counters.length && 'IntersectionObserver' in window && !reduceMotion) {
    var expoOut = function (t) { return t === 1 ? 1 : 1 - Math.pow(2, -10 * t); };
    function format(n, decimals) {
      return n.toLocaleString('en-AU', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    }
    function run(el) {
      var target = parseFloat(el.dataset.countTo);
      var decimals = (el.dataset.countTo.split('.')[1] || '').length;
      var start = null, DURATION = 1000;
      function step(now) {
        if (start === null) start = now;
        var t = Math.min(1, (now - start) / DURATION);
        el.textContent = format(target * expoOut(t), decimals) + (el.dataset.countSuffix || '');
        if (t < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    }
    counters.forEach(function (el) {
      el.textContent = format(0, (el.dataset.countTo.split('.')[1] || '').length) + (el.dataset.countSuffix || '');
    });
    var countObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        countObs.unobserve(e.target);
        run(e.target);
      });
    }, { threshold: 0.6 });
    counters.forEach(function (el) { countObs.observe(el); });
  }

  /* ---------- Home hero: orange gradient fades to the white page as soon as the user scrolls ---------- */
  var homeHero = document.querySelector('.home-hero');
  if (homeHero) {
    var rushed = false;
    var rushHero = function () { // scrolled before the intro sequence finished: play the rest in order, faster
      if (rushed || window.scrollY < 40) return;
      rushed = true; homeHero.classList.add('hero-rush');
    };
    window.addEventListener('scroll', rushHero, { passive: true });
    var fadeHero = function () { homeHero.classList.toggle('is-faded', window.scrollY > 40); };
    window.addEventListener('scroll', fadeHero, { passive: true });
    fadeHero();
  }

  /* ---------- Reveal: [data-reveal] fades in and rises once, when it scrolls into view ----------
     Elements with data-reveal-cols="N" stagger by their column in an N-column grid (150ms each),
     so a long grid never builds a long delay. Reduced motion shows everything at once. */
  var revealEls = [].slice.call(document.querySelectorAll('[data-reveal]'));
  if (revealEls.length) {
    revealEls.forEach(function (el) {
      var cols = parseInt(el.dataset.revealCols, 10);
      if (cols) el.style.setProperty('--i', [].indexOf.call(el.parentNode.children, el) % cols);
    });
    if (reduceMotion || !('IntersectionObserver' in window)) {
      revealEls.forEach(function (el) { el.classList.add('is-in'); });
    } else {
      var revealObs = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          // Scrolled past before it ever intersected (fast scroll, restored position): show it, never leave a hole
          if (!e.isIntersecting && e.boundingClientRect.top > 0) return;
          e.target.classList.add('is-in');
          revealObs.unobserve(e.target);
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.1 });
      revealEls.forEach(function (el) { revealObs.observe(el); });
    }
  }

  /* ---------- Story: copy + illustration that build up in stages ----------
     The block is CSS sticky; this works out which stage the scroll has reached and sets
     .is-s1 … .is-sN (cumulative) and data-current. Stages are triggered, not scrubbed:
     CSS plays each stage's short animation and reverses it on the way back up.
     On small screens there is no pin, so the stages play once in sequence when the
     illustration scrolls into view. Reduced motion shows the finished state. */
  document.querySelectorAll('.story').forEach(function (story) {
    var n = parseInt(story.dataset.stages, 10) || 1;
    var copy = story.querySelector('.story__copy');
    var figure = story.querySelector('[data-play-target]') || story.querySelector('.story__figure');
    var navEl = document.querySelector('.site-nav');
    var current = -1, reached = {};

    /* Numbers with data-count-stage count up from 0 when their stage is reached (expo.out,
       data-count-ms long) and reset when the visitor scrolls back above it, so they count
       again next time. Screen readers get the real value from a visually hidden twin. */
    var counts = [].slice.call(story.querySelectorAll('[data-count-stage]')).map(function (el) {
      return { el: el, to: parseFloat(el.textContent), stage: +el.dataset.countStage,
               ms: +el.dataset.countMs || 1000, on: false, raf: 0 };
    });
    function count(c, run) {
      cancelAnimationFrame(c.raf);
      c.on = run;
      if (!run) { c.el.textContent = '0'; return; }
      var start = null;
      (function step(now) {
        if (now === undefined) { c.raf = requestAnimationFrame(step); return; }
        if (start === null) start = now;
        var t = Math.min(1, (now - start) / c.ms);
        c.el.textContent = Math.round(c.to * (t === 1 ? 1 : 1 - Math.pow(2, -10 * t)));
        if (t < 1) c.raf = requestAnimationFrame(step);
      })();
    }

    function setStage(s) {
      if (s === current) return;
      current = s;
      for (var i = 1; i <= n; i++) story.classList.toggle('is-s' + i, i <= s);
      counts.forEach(function (c) { if ((c.stage <= s) !== c.on) count(c, c.stage <= s); });
      if (s > 0) story.dataset.current = s; else delete story.dataset.current;
      if (s > 0 && !reached[s]) {
        reached[s] = true;
        track('story_stage', { case_study: caseStudy || null, section: story.dataset.section, stage: s, of: n });
      }
    }

    if (reduceMotion) { for (var i = 1; i <= n; i++) story.classList.add('is-s' + i); return; }
    counts.forEach(function (c) { c.el.textContent = '0'; });

    function measure() { if (copy) story.style.setProperty('--story-copy-h', copy.offsetHeight + 'px'); }
    measure();
    window.addEventListener('resize', measure);

    var played = false;
    if ('IntersectionObserver' in window) {
      var playObs = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (!SMALL_SCREEN.matches || played || !e.isIntersecting) return;
          played = true;
          for (var s = 1; s <= n; s++) (function (s) { setTimeout(function () { setStage(s); }, (s - 1) * 1100); })(s);
        });
      }, { threshold: 0.6 });
      playObs.observe(figure);
    }

    var ticking = false;
    function update() {
      ticking = false;
      if (SMALL_SCREEN.matches) { if (!played) setStage(0); return; }
      var nav = navEl ? navEl.offsetHeight : 0;
      var avail = window.innerHeight - nav;
      var r = story.getBoundingClientRect();
      var scrolled = nav - r.top;                 // distance scrolled since the block pinned
      var step = (r.height - avail) / n;          // --story-step, read back from the layout
      var s = scrolled < -avail * 0.15 ? 0 : Math.min(n, Math.floor(Math.max(0, scrolled) / step) + 1);
      setStage(s);
    }
    window.addEventListener('scroll', function () {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });
    window.addEventListener('resize', update);
    update();
  });
})();
