/* mrpatel.com — /how-this-was-built: scroll steps through the prompt list.
   The track is tall and its stage is CSS sticky (site.css, .hb). This works out which prompt the scroll has
   reached, marks it active, fades the rest by distance (data-dist), slides the list so the active row sits at
   the stage's vertical centre, crossfades the image panel and moves the rail thumb. Prompts are not clickable.
   Below 700px (and without JS) the list is plain, so nothing here runs. */
(function () {
  'use strict';

  var root = document.querySelector('[data-hb]');
  if (!root) return;

  var stage = root.querySelector('.hb__stage');
  var viewport = root.querySelector('.hb__viewport');
  var list = root.querySelector('.hb__list');
  var items = [].slice.call(list.children);
  var shots = [].slice.call(root.querySelectorAll('.hb__shot'));
  var capLabel = root.querySelector('.hb__caption-label');
  var capCount = root.querySelector('.hb__caption-count');
  var total = parseInt(root.dataset.total, 10) || items.length;
  var navEl = document.querySelector('.site-nav');
  var marks = [].slice.call(root.querySelectorAll('.hb__mark'));
  var NEAR = 4; // rows either side of the active one that get a data-dist; everything further uses the CSS default
  var MARKS = [25, 50, 75, 100], sent = {};
  var current = -1, ticking = false;

  // The panel shows an image only on the prompts that have one; it is empty otherwise
  var imageAt = items.map(function (li) { return li.dataset.image || null; });
  var shotByKey = {};
  shots.forEach(function (s) { shotByKey[s.dataset.image] = s; });

  function isSticky() { return getComputedStyle(stage).position === 'sticky'; }

  function setDist(from, to, idx) {
    for (var i = Math.max(0, from); i <= Math.min(items.length - 1, to); i++) {
      var d = Math.abs(i - idx);
      if (d <= NEAR) items[i].dataset.dist = d; else delete items[i].dataset.dist;
    }
  }

  function place(idx) {
    var row = items[idx];
    var centre = viewport.clientHeight / 2;
    var y = row.offsetTop + row.offsetHeight / 2;
    list.style.transform = 'translateY(' + Math.round(centre - y) + 'px)';
  }

  function show(idx) {
    var prev = current;
    current = idx;
    if (prev >= 0) {
      items[prev].classList.remove('is-active');
      var pd = items[prev].querySelector('details'); if (pd) pd.open = false;
    }
    items[idx].classList.add('is-active');
    setDist(Math.min(prev < 0 ? idx : prev, idx) - NEAR - 1, Math.max(prev < 0 ? idx : prev, idx) + NEAR + 1, idx);
    place(idx);

    var key = imageAt[idx];
    shots.forEach(function (s) { s.classList.toggle('is-on', s.dataset.image === key); });
    var label = key && shotByKey[key] ? shotByKey[key].querySelector('.hb__label').textContent : '';
    capLabel.textContent = label;
    capCount.textContent = 'Prompt ' + Number(items[idx].dataset.n).toLocaleString('en-AU') + ' of ' + total.toLocaleString('en-AU');
    marks.forEach(function (m) { m.classList.toggle('is-here', Number(m.dataset.index) === idx); });
    root.classList.toggle('is-first', idx === 0);
    root.classList.toggle('is-last', idx === items.length - 1);
    root.classList.toggle('is-started', idx > 0);
  }

  function update() {
    ticking = false;
    if (!isSticky()) {
      list.style.transform = '';
      marks.forEach(function (m) { m.classList.remove('is-here'); });
      if (current >= 0) {
        items[current].classList.remove('is-active');
        items.forEach(function (li) { delete li.dataset.dist; });
        current = -1;
      }
      return;
    }
    var nav = navEl ? navEl.offsetHeight : 0;
    var max = root.offsetHeight - stage.offsetHeight;
    var scrolled = Math.min(max, Math.max(0, nav - root.getBoundingClientRect().top));
    var p = max > 0 ? scrolled / max : 0;
    var idx = items.length > 1 ? Math.round(p * (items.length - 1)) : 0;
    stage.style.setProperty('--hb-p', p.toFixed(4));
    if (idx !== current) show(idx);
    MARKS.forEach(function (m) {
      if (p * 100 >= m - 0.5 && !sent[m]) { sent[m] = true; if (window.track) window.track('prompt_index_progress', { percent: m, prompt: Number(items[idx].dataset.n), of: total }); }
    });
  }

  function request() {
    if (document.visibilityState === 'hidden') { update(); return; } // rAF pauses in hidden tabs
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }

  // Scroll position that puts row idx at the centre (the inverse of update())
  function scrollTarget(idx) {
    var nav = navEl ? navEl.offsetHeight : 0;
    var max = root.offsetHeight - stage.offsetHeight;
    var p = items.length > 1 ? idx / (items.length - 1) : 0;
    return Math.round(window.pageYOffset + root.getBoundingClientRect().top - nav + p * max);
  }
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Milestone buttons jump to their prompt
  [].forEach.call(root.querySelectorAll('.hb__mark'), function (b) {
    b.addEventListener('click', function () {
      if (!isSticky()) { items[Number(b.dataset.index)].scrollIntoView({ block: 'center' }); return; }
      window.scrollTo({ top: scrollTarget(Number(b.dataset.index)), behavior: reduce ? 'auto' : 'smooth' });
      if (window.track) window.track('prompt_index_milestone', { milestone: b.textContent.trim() });
    });
  });

  // Drag the rail thumb (or click the line) to scrub through the prompts
  var line = root.querySelector('.hb__rail-line');
  var thumbH = 36; // matches .hb__thumb height (2.25rem at 16px)
  function scrub(e) {
    var r = line.getBoundingClientRect();
    var p = Math.min(1, Math.max(0, (e.clientY - r.top - thumbH / 2) / (r.height - thumbH)));
    window.scrollTo(0, scrollTarget(Math.round(p * (items.length - 1))));
  }
  if (line) {
    line.addEventListener('pointerdown', function (e) {
      if (!isSticky()) return;
      e.preventDefault();
      line.setPointerCapture(e.pointerId);
      root.classList.add('is-scrubbing');
      scrub(e);
    });
    line.addEventListener('pointermove', function (e) { if (root.classList.contains('is-scrubbing')) scrub(e); });
    var end = function () { root.classList.remove('is-scrubbing'); };
    line.addEventListener('pointerup', end);
    line.addEventListener('pointercancel', end);
  }

  list.addEventListener('toggle', function () { if (current >= 0 && isSticky()) place(current); }, true); // opening a handoff group changes the row's height
  window.addEventListener('scroll', request, { passive: true });
  function replace() { if (current >= 0 && isSticky()) place(current); request(); } // new size or font metrics move the rows
  window.addEventListener('resize', replace);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(replace);

  update();
})();
