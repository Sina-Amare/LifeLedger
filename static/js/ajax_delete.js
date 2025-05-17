// static/js/ajax_delete.js

document.addEventListener("DOMContentLoaded", function () {
  const deleteModal = document.getElementById("delete-modal");
  // This selector targets the div that actually contains the modal's visible content and has transition classes.
  const modalDialogBox = deleteModal
    ? deleteModal.querySelector(".modal-dialog-box")
    : null;

  const confirmDeleteButton = document.getElementById("confirm-delete-button");
  const cancelDeleteButton = document.getElementById("cancel-delete-button");
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
    if (!deleteModal) {
      console.error("#delete-modal element not found in the DOM.");
      return;
    }
    if (!modalDialogBox) {
      console.error(
        ".modal-dialog-box element not found inside #delete-modal. Make sure it has this class."
      );
      // As a fallback, if modalDialogBox is not found, just show the main modal overlay.
      // This won't have the nice animation for the dialog box itself.
      deleteModal.classList.remove("hidden");
      return;
    }
    if (!confirmDeleteButton || !cancelDeleteButton || !modalEntryTitle) {
      console.error(
        "One or more modal action buttons or title element not found."
      );
      return;
    }

    modalEntryTitle.textContent = entryTitle;
    confirmDeleteButton.dataset.entryId = entryId;
    confirmDeleteButton.dataset.entryElementId = entryElementId;

    deleteModal.classList.remove("hidden");

    // Requesting a reflow can sometimes help ensure transitions apply correctly after display change.
    // void modalDialogBox.offsetWidth;

    setTimeout(() => {
      // Delay to allow display:flex to apply
      modalDialogBox.classList.remove("opacity-0", "scale-95");
      modalDialogBox.classList.add("opacity-100", "scale-100");
    }, 20);

    console.log(`Modal shown for entry ID: ${entryId}, Title: ${entryTitle}`);
  }

  function hideModal() {
    if (!deleteModal || !modalDialogBox) {
      console.error(
        "Modal elements not found for hiding. Cannot hide properly."
      );
      if (deleteModal) deleteModal.classList.add("hidden"); // At least hide the overlay
      return;
    }

    modalDialogBox.classList.remove("opacity-100", "scale-100");
    modalDialogBox.classList.add("opacity-0", "scale-95");

    setTimeout(() => {
      deleteModal.classList.add("hidden");
      if (confirmDeleteButton) {
        confirmDeleteButton.removeAttribute("data-entry-id");
        confirmDeleteButton.removeAttribute("data-entry-element-id");
      }
    }, 300); // Match CSS transition duration (e.g., duration-300)
    console.log("Modal hidden.");
  }

  function initializeDeleteButtons() {
    const deleteButtons = document.querySelectorAll(".delete-entry-button");
    deleteButtons.forEach((button) => {
      const newButton = button.cloneNode(true);
      if (button.parentNode) {
        button.parentNode.replaceChild(newButton, button);
      } else {
        console.warn(
          "Button for deletion has no parent, cannot re-attach listener.",
          button
        );
        return; // Skip if no parent
      }

      newButton.addEventListener("click", function () {
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
        // Guard against missing entryId
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
          console.log(
            "Fetch response status:",
            response.status,
            response.statusText
          );
          if (response.ok) {
            return response.json();
          } else {
            return response.text().then((text) => {
              console.error(
                "Server returned non-OK status:",
                response.status,
                response.statusText
              );
              console.error("Server response body (if any):", text);
              let errorMsg = `Server error: ${response.status} ${response.statusText}`;
              try {
                const errorData = JSON.parse(text);
                if (errorData && errorData.message)
                  errorMsg = errorData.message;
              } catch (e) {
                if (text && text.length < 200 && text.indexOf("<") === -1)
                  errorMsg = text;
              }
              throw new Error(errorMsg);
            });
          }
        })
        .then((data) => {
          hideModal();
          if (data && data.status === "success") {
            console.log(
              `Journal entry ${
                data.entry_id || entryId
              } deleted successfully. Message: ${data.message}`
            );
            const entryElement = document.getElementById(entryElementId);
            const listContainer = document.getElementById(
              "journal-entries-list"
            );
            if (entryElement) {
              if (
                listContainer &&
                entryElement.parentElement === listContainer
              ) {
                entryElement.remove();
                console.log(
                  `Removed element with ID ${entryElementId} from the list.`
                );
                const noEntriesMessage =
                  document.getElementById("no-entries-message");
                if (listContainer.children.length === 0 && noEntriesMessage) {
                  noEntriesMessage.classList.remove("hidden");
                }
              } else {
                console.log(
                  `Not on list page or element structure changed. Redirecting to /journal/`
                );
                window.location.replace("/journal/");
              }
            } else {
              console.log(
                `Element with ID ${entryElementId} not found, but deletion successful. Redirecting.`
              );
              window.location.replace("/journal/");
            }
          } else {
            console.error(
              "Deletion failed based on server response:",
              data ? data.message : "Unknown server response format"
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
          console.error("Error during deletion process:", error);
          alert(
            "An error occurred while trying to delete the journal entry: " +
              error.message
          );
        });
    });
  } else {
    console.warn(
      "#confirm-delete-button not found. Ensure modal HTML is present and ID is correct."
    );
  }

  if (cancelDeleteButton) {
    cancelDeleteButton.addEventListener("click", hideModal);
  } else {
    console.warn(
      "#cancel-delete-button not found. Ensure modal HTML is present and ID is correct."
    );
  }

  initializeDeleteButtons();
});
