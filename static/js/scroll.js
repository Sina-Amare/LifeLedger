// Add scroll animation for sections
document.addEventListener("DOMContentLoaded", () => {
  const sections = document.querySelectorAll(
    ".fade-in-section, .fade-in-right, .fade-in-left"
  );

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
        }
      });
    },
    {
      threshold: 0.1, // Trigger when 10% of the section is visible
    }
  );

  sections.forEach((section) => {
    observer.observe(section);
  });
});
