document.addEventListener("DOMContentLoaded", function () {
  const deleteModal = document.getElementById("delete-modal");
  const modalDialogBox = deleteModal
    ? deleteModal.querySelector(".modal-dialog-box")
    : null;
  const confirmDeleteButton = document.getElementById("confirm-delete-button");
  const cancelDeleteButton = document.getElementById("cancel-delete-button");
  const closeModalButton = document.getElementById("close-modal-x-button");
  const modalEntryTitle = document.getElementById("modal-entry-title");

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
    if (
      !deleteModal ||
      !modalDialogBox ||
      !confirmDeleteButton ||
      !cancelDeleteButton ||
      !modalEntryTitle
    ) {
      console.error("One or more modal elements not found.");
      return;
    }

    modalEntryTitle.textContent = entryTitle;
    confirmDeleteButton.dataset.entryId = entryId;
    confirmDeleteButton.dataset.entryElementId = entryElementId;

    deleteModal.classList.remove("hidden", "opacity-0");
    setTimeout(() => {
      deleteModal.classList.add("opacity-100");
      modalDialogBox.classList.remove("opacity-0", "scale-95");
      modalDialogBox.classList.add("opacity-100", "scale-100");
    }, 20);

    console.log(`Modal shown for entry ID: ${entryId}, Title: ${entryTitle}`);
  }

  function hideModal() {
    if (!deleteModal || !modalDialogBox) {
      console.error("Modal elements not found for hiding.");
      if (deleteModal) deleteModal.classList.add("hidden");
      return;
    }

    modalDialogBox.classList.remove("opacity-100", "scale-100");
    modalDialogBox.classList.add("opacity-0", "scale-95");
    deleteModal.classList.remove("opacity-100");

    setTimeout(() => {
      deleteModal.classList.add("hidden");
      confirmDeleteButton.removeAttribute("data-entry-id");
      confirmDeleteButton.removeAttribute("data-entry-elementId");
      modalEntryTitle.textContent = "";
    }, 300); // Match CSS transition duration
    console.log("Modal hidden.");
  }

  function initializeDeleteButtons() {
    const deleteButtons = document.querySelectorAll(".delete-entry-button");
    deleteButtons.forEach((button) => {
      button.addEventListener("click", function () {
        const entryId = this.dataset.entryId;
        const entryTitle = this.dataset.entryTitle;
        const entryElementId = `entry-${entryId}`;

        console.log("Delete button clicked.");
        console.log("  Entry ID:", entryId);
        console.log("  Entry Title:", entryTitle);
        console.log("  Element ID:", entryElementId);

        if (entryId) {
          showModal(entryTitle, entryId, entryElementId);
        } else {
          console.error("Error: Could not get entry ID from delete button.");
          alert("An error occurred. Could not get journal entry ID.");
        }
      });
    });
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

      const deleteUrl = `/journal/${entryId}/delete/`;
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
            } else {
              window.location.href = "/journal/";
            }
          } else {
            console.error(
              "Deletion failed:",
              data ? data.message : "Unknown error"
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
          console.error("Error during deletion:", error);
          alert(
            "An error occurred while deleting the journal entry: " +
              error.message
          );
        });
    });
  }

  if (cancelDeleteButton) {
    cancelDeleteButton.addEventListener("click", hideModal);
  }

  if (closeModalButton) {
    closeModalButton.addEventListener("click", hideModal);
  }

  // Handle Escape key to close modal
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !deleteModal.classList.contains("hidden")) {
      hideModal();
    }
  });

  initializeDeleteButtons();
});
