/* blog.js — comportements communs aux pages du blog.
   Reprend la logique de index.html : menu mobile, animations d'apparition,
   année du footer, et sélecteur particulier / professionnel.
   La clé localStorage 'qd_segment' est identique à celle du site : le choix
   du visiteur est conservé entre l'accueil et le blog. */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  const year = $('#year');
  if (year) year.textContent = new Date().getFullYear();

  const burger = $('#burger');
  const panel = $('#mobilePanel');
  if (burger && panel) {
    const closePanel = () => {
      panel.classList.remove('open');
      burger.setAttribute('aria-expanded', 'false');
    };
    burger.addEventListener('click', () => {
      const open = panel.classList.toggle('open');
      burger.setAttribute('aria-expanded', String(open));
    });
    panel.addEventListener('click', (e) => { if (e.target.matches('[data-close]')) closePanel(); });
    window.addEventListener('keydown', (e) => { if (e.key === 'Escape') closePanel(); });
  }

  const revealEls = $$('.reveal');
  if (revealEls.length && 'IntersectionObserver' in window) {
    const rev = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting) { en.target.classList.add('in'); rev.unobserve(en.target); }
      });
    }, { threshold: 0.14 });
    revealEls.forEach((el) => rev.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add('in'));
  }

  const segPart = $('#segPart');
  const segPro = $('#segPro');

  function setSegment(seg) {
    const isPro = seg === 'pro';
    document.body.setAttribute('data-theme', isPro ? 'pro' : 'particulier');
    if (segPart) segPart.setAttribute('aria-pressed', String(!isPro));
    if (segPro) segPro.setAttribute('aria-pressed', String(isPro));
    localStorage.setItem('qd_segment', seg);
  }

  if (segPart) segPart.addEventListener('click', () => setSegment('particulier'));
  if (segPro) segPro.addEventListener('click', () => setSegment('pro'));

  const saved = localStorage.getItem('qd_segment');
  setSegment(saved === 'pro' ? 'pro' : 'particulier');
})();
