// static/js/home_scripts.js
// JavaScript specific to home.html

document.addEventListener("DOMContentLoaded", function () {
  // --- Scroll-triggered animations for elements with .animate-on-scroll ---
  const observerOptions = {
    root: null, // Use the viewport as the root
    rootMargin: "0px", // No margin
    threshold: 0.15, // Trigger when 15% of the element is visible
  };

  const intersectionObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        // Optional: Unobserve after animation to save resources,
        // but this means it won't re-animate if user scrolls up and down.
        // observer.unobserve(entry.target);
      }
      // To make animations replay if they scroll out and back in:
      // else {
      //     entry.target.classList.remove('is-visible');
      // }
    });
  }, observerOptions);

  const elementsToAnimate = document.querySelectorAll(".animate-on-scroll");
  elementsToAnimate.forEach((el) => {
    // Apply animation delay from inline style if present
    // The actual animation is triggered by adding 'is-visible'
    const delay = el.style.animationDelay;
    if (delay) {
      // The delay is handled by CSS, JS just adds the class to trigger it
    }
    intersectionObserver.observe(el);
  });

  // --- Hero Title Letter-by-Letter Animation ---
  const heroTitle = document.querySelector(".hero-title-creative");
  if (heroTitle) {
    const text = heroTitle.textContent.trim(); // Get the original text
    heroTitle.innerHTML = ""; // Clear the original text to replace with spans

    text.split("").forEach((char, index) => {
      const span = document.createElement("span");
      span.textContent = char === " " ? "\u00A0" : char; // Preserve spaces
      // Apply animation delay for staggered effect.
      // The animation 'heroTitleLetterFlyIn' is defined in home_styles.css
      span.style.animationDelay = `${0.5 + index * 0.05}s`;
      heroTitle.appendChild(span);
    });
  }
});
