/**
 * Contains global JavaScript for the base template.
 * This includes initializing external libraries like Fancybox and handling
 * universal UI elements like the hamburger navigation menu.
 *
 * The delete modal logic has been moved to its own dedicated file, `ajax_delete.js`.
 */
document.addEventListener("DOMContentLoaded", function () {
  // --- Preloader Hiding Logic ---
  const preloader = document.getElementById("page-preloader");
  if (preloader) {
    preloader.style.display = "none";
    console.log("Preloader hidden on DOM load");
  }

  // --- Initialize Fancybox ---
  // Checks if the Fancybox library is available before trying to use it.
  if (typeof Fancybox !== "undefined") {
    Fancybox.bind("[data-fancybox]", {
      // Your custom options for Fancybox can go here.
    });
  } else {
    console.warn("Fancybox library not found. Image previews may not work.");
  }

  // --- Hamburger Menu Logic ---
  const hamburgerToggle = document.getElementById("hamburger-toggle");
  const hamburgerMenu = document.getElementById("hamburger-menu");

  if (hamburgerToggle && hamburgerMenu) {
    hamburgerToggle.addEventListener("click", function () {
      const isOpen = hamburgerMenu.classList.contains("open");
      hamburgerMenu.classList.toggle("open", !isOpen);
      hamburgerMenu.classList.toggle("hidden", isOpen);
      hamburgerToggle.setAttribute("aria-expanded", String(!isOpen));
    });

    // Close the menu when a click is registered outside of it.
    document.addEventListener("click", function (event) {
      if (
        hamburgerMenu.classList.contains("open") &&
        !hamburgerMenu.contains(event.target) &&
        !hamburgerToggle.contains(event.target)
      ) {
        hamburgerMenu.classList.remove("open");
        hamburgerMenu.classList.add("hidden");
        hamburgerToggle.setAttribute("aria-expanded", "false");
      }
    });

    // Close the menu when the 'Escape' key is pressed.
    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && hamburgerMenu.classList.contains("open")) {
        hamburgerMenu.classList.remove("open");
        hamburgerMenu.classList.add("hidden");
        hamburgerToggle.setAttribute("aria-expanded", "false");
      }
    });
  } else {
    console.warn("Hamburger menu elements not found.");
  }
});
