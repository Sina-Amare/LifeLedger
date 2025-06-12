/**
 * LifeLedger Global Delete Modal Handler
 *
 * This script manages all functionality for the global delete confirmation modal.
 * It attaches a single, smart event listener to the document to handle clicks
 * on any delete button, shows/hides the modal with animations, and performs
 * the deletion via an AJAX (Fetch) request. This approach is efficient and
 * avoids conflicts between multiple scripts.
 *
 * How it works:
 * 1. Listens for clicks on the entire document.
 * 2. Checks if the clicked element (or its parent) is a delete button.
 * 3. If so, it reads the data attributes (like entry title and delete URL) from the button.
 * 4. It then populates and displays the modal.
 * 5. It also handles the "Confirm" and "Cancel" button clicks within the modal.
 */
document.addEventListener("DOMContentLoaded", function () {
  // --- Element Cache ---
  // We get all the necessary modal elements once and store them for performance.
  const deleteModal = document.getElementById("delete-modal");
  const modalDialog = deleteModal
    ? deleteModal.querySelector(".modal-dialog-box")
    : null;
  const confirmDeleteBtn = document.getElementById("confirm-delete-button");
  const cancelDeleteBtn = document.getElementById("cancel-delete-button");
  const closeModalXBtn = document.getElementById("close-modal-x-button");
  const modalTitleSpan = document.getElementById("modal-entry-title");

  // If the modal HTML doesn't exist on the page, there's nothing to do.
  if (!deleteModal || !confirmDeleteBtn || !cancelDeleteBtn) {
    console.warn(
      "Delete modal components not found. The delete script is inactive."
    );
    return;
  }

  // --- State Management ---
  // A simple object to hold the data for the item currently being deleted.
  let activeDeleteContext = {
    deleteUrl: null,
    entryId: null,
    elementToRemoveId: null,
    redirectUrl: null,
  };

  /**
   * Retrieves the CSRF token required for secure POST requests in Django.
   * @param {string} name - The name of the cookie (usually 'csrftoken').
   * @returns {string} The CSRF token value.
   */
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  const csrftoken = getCookie("csrftoken");

  /**
   * Displays the modal with a smooth animation and sets the context for deletion.
   * @param {object} context - An object containing details about the item to delete.
   */
  function showModal(context) {
    activeDeleteContext = context; // Store the data for the confirm button to use.
    modalTitleSpan.textContent = context.entryTitle;

    deleteModal.classList.remove("hidden");
    // A tiny delay ensures the browser registers the change from 'hidden'
    // and can properly apply the transition for opacity.
    setTimeout(() => {
      deleteModal.classList.remove("opacity-0");
      modalDialog.classList.remove("opacity-0", "scale-95");
    }, 10);
  }

  /**
   * Hides the modal with an animation and clears the context.
   */
  function hideModal() {
    deleteModal.classList.add("opacity-0");
    modalDialog.classList.add("opacity-0", "scale-95");

    // Wait for the animation to finish before adding 'hidden' to remove it from the layout.
    setTimeout(() => {
      deleteModal.classList.add("hidden");
      // Reset the context so we don't accidentally delete the wrong thing later.
      activeDeleteContext = {};
    }, 300); // This duration should match your CSS transition time.
  }

  /**
   * The main delete action triggered by the confirm button.
   */
  function performDelete() {
    const { deleteUrl, entryId, elementToRemoveId, redirectUrl } =
      activeDeleteContext;

    if (!deleteUrl) {
      console.error("Deletion failed: No delete URL was provided.");
      hideModal();
      return;
    }

    // Disable the button to prevent multiple clicks while processing.
    confirmDeleteBtn.disabled = true;
    confirmDeleteBtn.textContent = "Deleting...";

    fetch(deleteUrl, {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrftoken,
      },
    })
      .then((response) => {
        if (!response.ok) {
          return response.json().then((err) => Promise.reject(err));
        }
        return response.json();
      })
      .then((data) => {
        if (data.status === "success") {
          // If a redirect URL was provided (on a detail page), go there.
          if (redirectUrl) {
            window.location.href = redirectUrl;
          } else {
            // Otherwise, find the entry on the list page and remove it with an animation.
            const elementToRemove = document.getElementById(elementToRemoveId);
            if (elementToRemove) {
              elementToRemove.style.transition = "opacity 0.3s, transform 0.3s";
              elementToRemove.style.opacity = "0";
              elementToRemove.style.transform = "scale(0.9)";
              setTimeout(() => elementToRemove.remove(), 300);
            }
          }
        } else {
          throw new Error(data.message || "An unknown error occurred.");
        }
      })
      .catch((error) => {
        console.error("Error during deletion:", error);
        alert(
          `Could not delete the entry. Error: ${
            error.message || "Please try again."
          }`
        );
      })
      .finally(() => {
        // Always re-enable the button and hide the modal.
        confirmDeleteBtn.disabled = false;
        confirmDeleteBtn.textContent = "Yes, Delete";
        hideModal();
      });
  }

  // --- Master Event Listener ---
  // Instead of attaching listeners to each button, we listen on the whole document.
  // This is more efficient and automatically works for content loaded later via AJAX.
  document.addEventListener("click", function (event) {
    const deleteButton = event.target.closest(".delete-entry-button");

    if (deleteButton) {
      event.preventDefault(); // Stop any default button action.

      // Gather all the necessary info from the button's data attributes.
      const context = {
        entryTitle: deleteButton.dataset.entryTitle,
        entryId: deleteButton.dataset.entryId,
        deleteUrl: deleteButton.dataset.deleteUrl,
        elementToRemoveId: `entry-group-${deleteButton.dataset.entryId}`,
        redirectUrl: deleteButton.dataset.redirectUrl,
      };
      showModal(context);
    }
  });

  // Attach listeners for the modal's own controls.
  confirmDeleteBtn.addEventListener("click", performDelete);
  cancelDeleteBtn.addEventListener("click", hideModal);
  closeModalXBtn.addEventListener("click", hideModal);
});
