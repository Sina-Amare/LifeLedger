// static/js/dashboard_scripts.js
// JavaScript specific to dashboard.html

document.addEventListener("DOMContentLoaded", function () {
  // --- Fade-in animations for elements with .fade-in-element ---
  const fadeElements = document.querySelectorAll(".fade-in-element");
  fadeElements.forEach((el, index) => {
    // Use the delay from inline style if present, otherwise calculate a stagger
    if (!el.style.animationDelay) {
      el.style.animationDelay = `${0.15 + index * 0.1}s`; // Default stagger
    }
    // The 'fade-in-element' class itself triggers the animation via CSS.
    // No need to add/remove classes here for this specific animation if it's auto-playing.
  });

  // --- Help Popover Functionality ---
  const helpIcons = document.querySelectorAll(".help-icon");
  helpIcons.forEach((icon) => {
    const popoverId = icon.dataset.target;
    const popover = document.getElementById(popoverId);

    if (popover) {
      icon.addEventListener("mouseenter", () => {
        popover.classList.add("active");
      });
      icon.addEventListener("mouseleave", () => {
        if (!popover.classList.contains("click-active")) {
          popover.classList.remove("active");
        }
      });

      icon.addEventListener("click", (e) => {
        e.preventDefault();
        document
          .querySelectorAll(".help-popover.click-active")
          .forEach((otherPopover) => {
            if (otherPopover !== popover) {
              otherPopover.classList.remove("active", "click-active");
            }
          });
        popover.classList.toggle("click-active");
        popover.classList.toggle("active");
      });
    } else {
      console.warn(
        `Popover with ID '${popoverId}' not found for help icon:`,
        icon
      );
    }
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".help-icon") && !e.target.closest(".help-popover")) {
      document
        .querySelectorAll(".help-popover.click-active")
        .forEach((popover) => {
          popover.classList.remove("active", "click-active");
        });
    }
  });

  // --- Dynamic Welcome Quote (Optional, if you want to change it from the static one) ---
  const welcomeQuoteElement = document.getElementById(
    "dashboard-welcome-quote"
  );
  if (welcomeQuoteElement) {
    const quotes = [
      // Ensuring i18n tags are not in JS strings directly if this script is static.
      // For dynamic quotes with i18n, pass them from the view or use a different approach.
      "Every entry is a step toward self-discovery.",
      "Today is a new page. Write your story.",
      "Reflection is the mirror of the soul.",
      "What wonderful thought will you capture today?",
    ];
    // To make it dynamic on each load:
    // welcomeQuoteElement.textContent = quotes[Math.floor(Math.random() * quotes.length)];
  }

  // --- Writing Prompt Functionality ---
  // Make sure showWritingPrompt is globally accessible if called by onclick
  window.showWritingPrompt = function () {
    const prompts = [
      // Same i18n concern as above for static JS file.
      "What's a moment you're grateful for today?",
      "Describe a challenge you faced recently and how you overcame it.",
      "What does your dream day look like?",
      "Write about a memory that always makes you smile.",
      "What's something new you learned this week?",
      "How do you feel right now, and why?",
      "What’s a goal you’re working toward, and what’s your next step?",
    ];
    const randomPrompt = prompts[Math.floor(Math.random() * prompts.length)];
    const promptTextElement = document.getElementById("writing-prompt-text");
    if (promptTextElement) {
      promptTextElement.textContent = randomPrompt;
    } else {
      console.warn("Element with ID 'writing-prompt-text' not found.");
    }
  };
  // Initialize with a prompt if the element exists
  if (document.getElementById("writing-prompt-text")) {
    // Call it to set an initial prompt.
    // If the textContent is already set by Django template, this might override it.
    // Consider if you want an initial JS-set prompt or rely on Django's {% trans %}.
    // For now, let's assume the initial text is set by Django, and JS changes it on click.
    // showWritingPrompt();
  }
});
