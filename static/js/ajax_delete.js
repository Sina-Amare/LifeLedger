// static/js/ajax_delete.js
document.addEventListener("DOMContentLoaded", function () {
  const deleteModal = document.getElementById("delete-modal"); // This is your global modal from base.html
  const modalDialogBox = deleteModal
    ? deleteModal.querySelector(".modal-dialog-box") // Assuming this class exists on your dialog
    : null;
  const confirmDeleteButton = document.getElementById("confirm-delete-button");
  const cancelDeleteButton = document.getElementById("cancel-delete-button");
  const closeModalButton = document.getElementById("close-modal-x-button"); // Assuming this is your 'X' close button
  const modalEntryTitle = document.getElementById("modal-entry-title");

  const pageModalBackdrop = document.getElementById("pageModalBackdrop");

  if (!deleteModal) {
    console.warn(
      "Global delete modal (ID 'delete-modal') not found. Delete functionality might be impaired."
    );
  }
  if (!pageModalBackdrop) {
    console.warn(
      "Page modal backdrop (ID 'pageModalBackdrop') not found. Modal will not have a backdrop."
    );
  }

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith(name + "=")) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  const csrftoken = getCookie("csrftoken");

  function showModal(entryTitle, entryId, entryElementId) {
    if (!deleteModal || !confirmDeleteButton || !modalEntryTitle) {
      console.error(
        "Core modal elements (deleteModal, confirmDeleteButton, modalEntryTitle) not found for showing."
      );
      return;
    }

    modalEntryTitle.textContent = entryTitle;
    confirmDeleteButton.dataset.entryId = entryId;
    confirmDeleteButton.dataset.entryElementId = entryElementId;

    if (pageModalBackdrop) {
      pageModalBackdrop.classList.remove("hidden");
      // Ensure backdrop is visually apparent
      pageModalBackdrop.style.opacity = "1"; // Tailwind's bg-opacity-60 should handle the color
    }

    // --- DIAGNOSTIC: Force modal visibility ---
    deleteModal.classList.remove("hidden"); // Standard way
    deleteModal.style.display = "flex"; // Force display type if 'hidden' didn't set it right
    deleteModal.style.opacity = "1"; // Force opacity
    deleteModal.style.zIndex = "50"; // Ensure it's above backdrop (backdrop is z-40)
    // --- END DIAGNOSTIC ---

    if (modalDialogBox) {
      // Standard transition classes
      modalDialogBox.classList.remove("opacity-0", "scale-95");
      modalDialogBox.classList.add("opacity-100", "scale-100");
      // --- DIAGNOSTIC for dialog box ---
      modalDialogBox.style.opacity = "1";
      modalDialogBox.style.transform = "scale(1)";
      // --- END DIAGNOSTIC ---
    } else {
      console.warn(
        ".modal-dialog-box not found. Only #delete-modal opacity will be directly set."
      );
    }
    console.log(`Modal shown for entry ID: ${entryId}, Title: ${entryTitle}`);
  }

  function hideModal() {
    if (pageModalBackdrop) {
      pageModalBackdrop.classList.add("hidden");
      pageModalBackdrop.style.opacity = "0"; // Reset diagnostic style
    }

    if (!deleteModal) {
      console.error("Modal element not found for hiding.");
      return;
    }

    // Reset diagnostic styles
    deleteModal.style.display = "";
    deleteModal.style.opacity = "";
    // deleteModal.style.zIndex = ''; // Or reset to its original if known

    // Standard transition classes for hiding
    if (modalDialogBox) {
      modalDialogBox.classList.remove("opacity-100", "scale-100");
      modalDialogBox.classList.add("opacity-0", "scale-95");
      // Reset diagnostic styles for dialog box
      modalDialogBox.style.opacity = "";
      modalDialogBox.style.transform = "";
    }
    deleteModal.classList.remove("opacity-100"); // For class-based fade-out
    deleteModal.classList.add("opacity-0"); // Ensure it starts fade out if not already

    setTimeout(() => {
      deleteModal.classList.add("hidden");
      if (confirmDeleteButton) {
        confirmDeleteButton.removeAttribute("data-entry-id");
        confirmDeleteButton.removeAttribute("data-entry-elementId");
      }
      if (modalEntryTitle) {
        modalEntryTitle.textContent = "";
      }
    }, 300);
    console.log("Modal hidden.");
  }

  function initializeDeleteButtons() {
    const deleteButtons = document.querySelectorAll(".delete-entry-button");
    deleteButtons.forEach((button) => {
      button.removeEventListener("click", handleDeleteButtonClick);
      button.addEventListener("click", handleDeleteButtonClick);
    });
  }

  function handleDeleteButtonClick() {
    const entryId = this.dataset.entryId;
    const entryTitle = this.dataset.entryTitle;
    const entryElementId = `entry-${entryId}`;

    console.log("Delete button clicked.");
    console.log("  Entry ID:", entryId);
    console.log("  Entry Title:", entryTitle);
    console.log("  Element ID to remove:", entryElementId);

    if (entryId) {
      showModal(entryTitle, entryId, entryElementId);
    } else {
      console.error("Error: Could not get entry ID from delete button.");
      alert("An error occurred. Could not get journal entry ID.");
    }
  }

  if (confirmDeleteButton) {
    confirmDeleteButton.addEventListener("click", function () {
      const entryId = this.dataset.entryId;
      const entryElementId = this.dataset.entryElementId;

      if (!entryId) {
        console.error(
          "Error: Confirm delete clicked but entry ID not found on button."
        );
        alert("An error occurred. Entry ID missing for deletion.");
        hideModal();
        return;
      }

      const deleteUrl = `/journal/${entryId}/delete/`; // Removed "entry/" and changed "ajax_delete/" to "delete/"
      console.log(
        "Confirm delete clicked. Sending POST request to:",
        deleteUrl
      );

      fetch(deleteUrl, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrftoken,
        },
      })
        .then((response) => {
          if (!response.ok) {
            return response.text().then((text) => {
              throw new Error(
                `Server error: ${response.status} ${
                  text || response.statusText
                }`
              );
            });
          }
          return response.json();
        })
        .then((data) => {
          hideModal();
          if (data && data.status === "success") {
            console.log(
              `Journal entry ${data.entry_id || entryId} deleted successfully.`
            );
            const entryElement = document.getElementById(entryElementId);
            if (entryElement) {
              entryElement.style.transition = "opacity 0.5s ease";
              entryElement.style.opacity = "0";
              setTimeout(() => {
                entryElement.remove();
                console.log(`Removed element with ID ${entryElementId}.`);
                const listContainer = document.getElementById(
                  "journal-entries-list"
                );
                if (listContainer && listContainer.children.length === 0) {
                  const noEntriesMessage =
                    document.getElementById("no-entries-message");
                  if (noEntriesMessage)
                    noEntriesMessage.classList.remove("hidden");
                }
              }, 500);
            } else {
              console.warn(
                `Element with ID ${entryElementId} not found for removal. Reloading page as fallback.`
              );
              window.location.href = "/journal/"; // Hardcoded fallback
            }
          } else {
            console.error(
              "Deletion failed:",
              data ? data.message : "Unknown error from server"
            );
            alert(
              "Failed to delete journal entry: " +
                (data && data.message
                  ? data.message
                  : "Server reported an issue.")
            );
          }
        })
        .catch((error) => {
          hideModal();
          console.error("Error during deletion fetch operation:", error);
          alert(
            "An error occurred while deleting the journal entry: " +
              error.message
          );
        });
    });
  } else {
    console.warn(
      "Confirm delete button (ID 'confirm-delete-button') not found."
    );
  }

  if (cancelDeleteButton) {
    cancelDeleteButton.addEventListener("click", hideModal);
  } else {
    console.warn("Cancel delete button (ID 'cancel-delete-button') not found.");
  }

  if (closeModalButton) {
    closeModalButton.addEventListener("click", hideModal);
  } else {
    console.info(
      "Modal close 'X' button (ID 'close-modal-x-button') not found (optional)."
    );
  }

  document.addEventListener("keydown", (event) => {
    if (
      event.key === "Escape" &&
      deleteModal &&
      !deleteModal.classList.contains("hidden")
    ) {
      hideModal();
    }
  });

  initializeDeleteButtons();
});
