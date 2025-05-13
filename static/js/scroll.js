// Add scroll animation functionality for sections
document.addEventListener("DOMContentLoaded", () => {
  // Select elements with animation classes
  const sections = document.querySelectorAll(
    ".fade-in-section, .fade-in-right, .fade-in-left"
  );

  // Create a new Intersection Observer
  // This observer watches elements and triggers a callback when they enter or exit the viewport
  const observer = new IntersectionObserver(
    (entries) => {
      // Iterate over each observed element's entry
      entries.forEach((entry) => {
        // If the element is intersecting (visible in the viewport)
        if (entry.isIntersecting) {
          // Add the 'visible' class to trigger the animation
          entry.target.classList.add("visible");
          // Optionally, unobserve the element after it becomes visible
          // observer.unobserve(entry.target);
        }
        // If you want elements to animate again when scrolling back up,
        // you would add an else block here to remove the 'visible' class
        // else {
        //   entry.target.classList.remove("visible");
        // }
      });
    },
    {
      // Options for the observer
      // threshold: 0.1 means the callback is triggered when 10% of the element is visible
      threshold: 0.1,
      // rootMargin can be used to expand or shrink the viewport area used for detection
      // rootMargin: "0px 0px -50px 0px" // Example: Trigger when 50px from the bottom of the viewport
    }
  );

  // Start observing each selected section
  sections.forEach((section) => {
    observer.observe(section);
  });
});
