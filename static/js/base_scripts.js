// static/js/base_scripts.js

document.addEventListener("DOMContentLoaded", function () {
  // Preloader Hiding Logic
  const preloader = document.getElementById("page-preloader");
  if (preloader) {
    // Since base.html already sets display: none, we just ensure it's hidden
    preloader.style.display = "none";
    console.log("Preloader hidden on DOM load");
  }

  // Initialize Fancybox
  if (typeof Fancybox !== "undefined") {
    Fancybox.bind("[data-fancybox]", {});
  } else {
    console.warn("Fancybox library not found. Image previews may not work.");
  }

  // Navbar Entrance Animation Control (Temporarily Disabled for Debugging)
  const navbar = document.getElementById("main-navbar");
  if (navbar) {
    // Skip animation for now to debug click issue
    navbar.style.opacity = "1";
    navbar.style.transform = "translateY(0)";
    console.log("Navbar animation skipped, set to visible");
  }

  // Global Delete Modal Interaction Logic
  const deleteModal = document.getElementById("delete-modal");
  const modalDialog = deleteModal
    ? deleteModal.querySelector(".modal-dialog-box")
    : null;
  const closeModalXButton = document.getElementById("close-modal-x-button");
  const cancelDeleteButton = document.getElementById("cancel-delete-button");

  window.showDeleteModal = function () {
    if (!deleteModal || !modalDialog) {
      console.error(
        "showDeleteModal: Modal or modal dialog element not found."
      );
      return;
    }
    deleteModal.classList.remove("hidden");
    deleteModal.classList.remove("opacity-0");
    modalDialog.style.opacity = "0";
    modalDialog.style.transform = "scale(0.95) translateY(10px)";

    setTimeout(() => {
      deleteModal.classList.add("modal-entering");
      modalDialog.style.opacity = "1";
      modalDialog.style.transform = "scale(1) translateY(0)";
      console.log("Delete modal shown, z-index:", deleteModal.style.zIndex);
    }, 10);

    setTimeout(() => {
      if (deleteModal) deleteModal.classList.remove("modal-entering");
    }, 200);
  };

  window.hideDeleteModal = function () {
    if (!deleteModal || !modalDialog) {
      console.error(
        "hideDeleteModal: Modal or modal dialog element not found."
      );
      return;
    }
    deleteModal.classList.add("modal-exiting");

    setTimeout(() => {
      deleteModal.classList.add("hidden", "opacity-0");
      deleteModal.classList.remove("modal-exiting");
      console.log("Delete modal hidden, display:", deleteModal.style.display);
    }, 150);
  };

  if (closeModalXButton) {
    closeModalXButton.addEventListener("click", window.hideDeleteModal);
  } else {
    console.warn("#close-modal-x-button not found.");
  }

  if (cancelDeleteButton) {
    cancelDeleteButton.addEventListener("click", window.hideDeleteModal);
  } else {
    console.warn("#cancel-delete-button not found.");
  }

  if (deleteModal) {
    window.addEventListener("keydown", (event) => {
      if (
        event.key === "Escape" &&
        !deleteModal.classList.contains("hidden") &&
        !deleteModal.classList.contains("modal-exiting")
      ) {
        window.hideDeleteModal();
      }
    });
    deleteModal.addEventListener("click", function (event) {
      if (event.target === deleteModal) {
        window.hideDeleteModal();
      }
    });
  }

  // Hamburger Menu Logic
  const hamburgerToggle = document.getElementById("hamburger-toggle");
  const hamburgerMenu = document.getElementById("hamburger-menu");

  if (hamburgerToggle && hamburgerMenu) {
    hamburgerToggle.addEventListener("click", function () {
      const isOpen = hamburgerMenu.classList.contains("open");
      hamburgerMenu.classList.toggle("open", !isOpen);
      hamburgerMenu.classList.toggle("hidden", isOpen);
      hamburgerToggle.setAttribute("aria-expanded", !isOpen);
      console.log(`Hamburger menu ${!isOpen ? "opened" : "closed"}`);
    });

    // Close menu when clicking outside
    document.addEventListener("click", function (event) {
      if (
        !hamburgerMenu.contains(event.target) &&
        !hamburgerToggle.contains(event.target) &&
        hamburgerMenu.classList.contains("open")
      ) {
        hamburgerMenu.classList.remove("open");
        hamburgerMenu.classList.add("hidden");
        hamburgerToggle.setAttribute("aria-expanded", "false");
        console.log("Hamburger menu closed due to outside click");
      }
    });

    // Close menu on Escape key
    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && hamburgerMenu.classList.contains("open")) {
        hamburgerMenu.classList.remove("open");
        hamburgerMenu.classList.add("hidden");
        hamburgerToggle.setAttribute("aria-expanded", "false");
        console.log("Hamburger menu closed via Escape key");
      }
    });
  } else {
    console.warn("Hamburger toggle or menu not found.");
  }

  // Debug navbar click events
  const navbarLinks = document.querySelectorAll(
    "#main-navbar a, #main-navbar button"
  );
  navbarLinks.forEach((link) => {
    link.addEventListener("click", function (e) {
      console.log("Navbar item clicked:", this.textContent || this.title);
      console.log(
        "Computed z-index:",
        window.getComputedStyle(document.getElementById("main-navbar")).zIndex
      );
      console.log(
        "Computed pointer-events:",
        window.getComputedStyle(this).pointerEvents
      );
      console.log("Element details:", this);
    });
    link.addEventListener("mousedown", function (e) {
      console.log("Navbar item mousedown:", this.textContent || this.title);
    });
  });
});
