// Motion follows the Portfolio Design System (claude.ai/artifact/MBTJo1Wj2NGr45ewCX29rN): one soft-landing ease, staggered, never bouncy.
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (window.gsap && !reduced) {
  gsap.registerPlugin(ScrollTrigger);
  const ease = "expo.out"; // ~ cubic-bezier(0.16, 1, 0.3, 1)

  // Load sequence: header, hero image, headline
  const tl = gsap.timeline({ defaults: { ease } });
  tl.from(".header > *", { opacity: 0, y: -12, duration: 1, stagger: 0.1 }, 0.2)
    .from(".hero__image", { clipPath: "inset(100% 0 0 0)", duration: 1.4 }, 0.2)
    .from(".hero__image img", { scale: 1.25, duration: 1.8 }, 0.2)
    .from("[data-split] .line > span", { yPercent: 110, duration: 1, stagger: 0.12 }, 0.8)
    .from(".hero__band .dek", { opacity: 0, y: 12, duration: 1 }, 1.1);

  // Giant wordmark drifts horizontally as you scroll
  gsap.fromTo(".hero__word", { xPercent: 0 }, {
    xPercent: -25, ease: "none",
    scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: true },
  });

  // Cards: image clip reveal, then text rises
  gsap.utils.toArray(".card").forEach((card) => {
    const st = { trigger: card, start: "top 80%" };
    gsap.from(card.querySelector(".card__img"), { clipPath: "inset(0 0 100% 0)", duration: 1.2, ease, scrollTrigger: st });
    gsap.from(card.querySelectorAll(".card__body > *"), { opacity: 0, y: 24, duration: 1, stagger: 0.1, delay: 0.3, ease, scrollTrigger: st });
  });
}
