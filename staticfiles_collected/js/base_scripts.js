document.addEventListener("DOMContentLoaded", function () {
  // Preloader Hiding Logic
  const preloader = document.getElementById("page-preloader");
  if (preloader) {
    preloader.classList.remove("hidden");
    window.addEventListener("load", () => {
      setTimeout(() => {
        preloader.classList.add("hidden");
      }, 100); // Reduced from 200ms to 100ms
    });
  }

  // Initialize Fancybox
  if (typeof Fancybox !== "undefined") {
    Fancybox.bind("[data-fancybox]", {});
  } else {
    console.warn("Fancybox library not found. Image previews may not work.");
  }

  // Navbar Entrance Animation Control
  const navbar = document.getElementById("main-navbar");
  if (navbar) {
    const hasAnimated = sessionStorage.getItem("navbarAnimated");
    if (!hasAnimated) {
      navbar.classList.add("navbar-animate-on-load");
      sessionStorage.setItem("navbarAnimated", "true");
    } else {
      navbar.style.opacity = "1";
      navbar.style.transform = "translateY(0)";
    }
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
    }, 10);

    setTimeout(() => {
      if (deleteModal) deleteModal.classList.remove("modal-entering");
    }, 200); // Reduced from 400ms to 200ms
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
    }, 150); // Reduced from 300ms to 150ms
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
});
