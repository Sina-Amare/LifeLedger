// static/js/base_scripts.js
// Contains logic for preloader, Fancybox, Navbar animation, and Delete Modal

document.addEventListener("DOMContentLoaded", function () {
  // --- Preloader Hiding Logic ---
  const preloader = document.getElementById("page-preloader");
  if (preloader) {
    // Ensure preloader is visible initially
    preloader.classList.remove("hidden");
    window.addEventListener("load", () => {
      // Wait a brief moment after load for content to render, then hide preloader
      setTimeout(() => {
        preloader.classList.add("hidden");
      }, 200); // Adjust delay as needed
    });
  }

  // --- Initialize Fancybox ---
  // Ensure Fancybox is loaded before trying to use it
  if (typeof Fancybox !== "undefined") {
    Fancybox.bind("[data-fancybox]", {
      // Optional: Add any global Fancybox configurations here
    });
  } else {
    console.warn("Fancybox library not found. Image previews may not work.");
  }

  // --- Navbar Entrance Animation Control ---
  const navbar = document.getElementById("main-navbar");
  if (navbar) {
    const hasAnimated = sessionStorage.getItem("navbarAnimated");
    if (!hasAnimated) {
      // If not animated yet in this session, add animation class
      navbar.classList.add("navbar-animate-on-load");
      sessionStorage.setItem("navbarAnimated", "true"); // Mark as animated for this session
    } else {
      // If already animated, ensure it's immediately visible without animation
      navbar.style.opacity = "1";
      navbar.style.transform = "translateY(0)";
    }
  }

  // --- Global Delete Modal Interaction Logic ---
  const deleteModal = document.getElementById("delete-modal");
  const modalDialog = deleteModal
    ? deleteModal.querySelector(".modal-dialog-box")
    : null;
  const closeModalXButton = document.getElementById("close-modal-x-button");
  const cancelDeleteButton = document.getElementById("cancel-delete-button"); // This is the "Cancel" button inside the modal

  // Function to show the delete modal with animation
  // This function will be called by other scripts (e.g., ajax_delete.js)
  window.showDeleteModal = function () {
    if (!deleteModal || !modalDialog) {
      console.error(
        "showDeleteModal: Modal or modal dialog element not found."
      );
      return;
    }
    deleteModal.classList.remove("hidden"); // Make modal container visible

    // Trigger animations shortly after display to ensure they play
    // Reset initial state for animation
    deleteModal.classList.remove("opacity-0"); // Ensure backdrop is not transparent
    modalDialog.style.opacity = "0";
    modalDialog.style.transform = "scale(0.95) translateY(10px)";

    setTimeout(() => {
      // Apply entering animations
      deleteModal.classList.add("modal-entering");
      modalDialog.style.opacity = "1";
      modalDialog.style.transform = "scale(1) translateY(0)";
    }, 10); // Small delay for CSS to catch up

    // Remove 'modal-entering' after animation duration to clean up
    // This timeout should roughly match the duration of modalDialogBounceIn
    setTimeout(() => {
      if (deleteModal) deleteModal.classList.remove("modal-entering");
    }, 400); // e.g., 0.4s for modalDialogBounceIn
  };

  // Function to hide the delete modal with animation
  window.hideDeleteModal = function () {
    if (!deleteModal || !modalDialog) {
      console.error(
        "hideDeleteModal: Modal or modal dialog element not found."
      );
      return;
    }
    deleteModal.classList.add("modal-exiting"); // Add class to trigger exit animations

    // After exit animation, hide the modal completely
    // This timeout should roughly match the duration of modalBackdropFadeOut / modalDialogBounceOut
    setTimeout(() => {
      deleteModal.classList.add("hidden", "opacity-0");
      deleteModal.classList.remove("modal-exiting");
    }, 300);
  };

  // Event listeners for modal close actions (X button and Cancel button)
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

  // Accessibility: Close modal with Escape key or by clicking outside on the backdrop
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
    // Close if backdrop (deleteModal itself) is clicked
    deleteModal.addEventListener("click", function (event) {
      if (event.target === deleteModal) {
        window.hideDeleteModal();
      }
    });
  }
});
