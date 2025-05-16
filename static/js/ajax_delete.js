// static/js/ajax_delete.js

document.addEventListener("DOMContentLoaded", function () {
  const deleteModal = document.getElementById("delete-modal");
  // Ensure this selector accurately targets the inner dialog box that has transition classes.
  const modalDialogBox = deleteModal
    ? deleteModal.querySelector(".modal-dialog-box")
    : null;

  const confirmDeleteButton = document.getElementById("confirm-delete-button");
  const cancelDeleteButton = document.getElementById("cancel-delete-button");
  const modalEntryTitle = document.getElementById("modal-entry-title");

  // Function to get CSRF token from cookie
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

  // Function to show the modal
  function showModal(entryTitle, entryId, entryElementId) {
    if (
      deleteModal &&
      modalDialogBox &&
      confirmDeleteButton &&
      cancelDeleteButton &&
      modalEntryTitle
    ) {
      modalEntryTitle.textContent = entryTitle;
      confirmDeleteButton.dataset.entryId = entryId;
      confirmDeleteButton.dataset.entryElementId = entryElementId;

      deleteModal.classList.remove("hidden"); // Show the overlay and modal container

      // Force a reflow before adding transition classes to ensure animation plays
      // void modalDialogBox.offsetWidth; // This is a common trick to trigger reflow

      // Add a slight delay to allow the display property to take effect before transitioning
      setTimeout(() => {
        modalDialogBox.classList.remove("opacity-0", "scale-95");
        modalDialogBox.classList.add("opacity-100", "scale-100");
      }, 20); // 20ms should be enough

      console.log(`Modal shown for entry ID: ${entryId}, Title: ${entryTitle}`);
    } else {
      console.error(
        "Error: Crucial modal elements (deleteModal, modalDialogBox, etc.) not found in the DOM."
      );
      if (!deleteModal) console.error("Could not find #delete-modal element.");
      if (!modalDialogBox)
        console.error("Could not find .modal-dialog-box inside #delete-modal.");
    }
  }

  // Function to hide the modal
  function hideModal() {
    if (deleteModal && modalDialogBox) {
      modalDialogBox.classList.remove("opacity-100", "scale-100");
      modalDialogBox.classList.add("opacity-0", "scale-95");

      // Wait for the transition to finish before hiding the overlay
      // This timeout duration should match your CSS transition duration (e.g., duration-300 in Tailwind is 300ms)
      setTimeout(() => {
        deleteModal.classList.add("hidden");
        // Clear data attributes from confirm button when modal is hidden
        if (confirmDeleteButton) {
          // Check if button exists
          confirmDeleteButton.removeAttribute("data-entry-id");
          confirmDeleteButton.removeAttribute("data-entry-element-id");
        }
      }, 300);
      console.log("Modal hidden.");
    } else {
      console.error(
        "Error: Modal elements (deleteModal, modalDialogBox) not found for hiding."
      );
    }
  }

  // Function to initialize delete buttons
  function initializeDeleteButtons() {
    const deleteButtons = document.querySelectorAll(".delete-entry-button");
    deleteButtons.forEach((button) => {
      // Clone and replace to remove any old listeners and ensure fresh ones
      const newButton = button.cloneNode(true);
      button.parentNode.replaceChild(newButton, button);

      newButton.addEventListener("click", function () {
        const entryId = this.dataset.entryId;
        const entryTitle = this.dataset.entryTitle;
        const entryElementId = `entry-${entryId}`; // Used to remove element from list page

        console.log("Delete button clicked.");
        console.log("Read entry ID from data attribute:", entryId);
        console.log("Read entry title from data attribute:", entryTitle);
        console.log("Constructed entry element ID:", entryElementId);

        if (entryId) {
          showModal(entryTitle, entryId, entryElementId);
        } else {
          console.error("Error: Could not get entry ID from delete button.");
          alert("An error occurred. Could not get journal entry ID.");
        }
      });
    });
  }

  // Add event listener to the Confirm Delete button in the modal
  if (confirmDeleteButton) {
    confirmDeleteButton.addEventListener("click", function () {
      const entryId = this.dataset.entryId;
      const entryElementId = this.dataset.entryElementId;
      const deleteUrl = `/journal/${entryId}/delete/`;

      console.log("Confirm delete clicked.");
      // console.log("Entry ID:", entryId); // Already logged above
      // console.log("Element ID to remove/check:", entryElementId); // Already logged above
      console.log("Sending POST request to:", deleteUrl);

      if (entryId) {
        fetch(deleteUrl, {
          method: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": csrftoken,
          },
        })
          .then((response) => {
            console.log("Fetch response status:", response.status);
            console.log("Fetch response status text:", response.statusText);
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
      } else {
        console.error(
          "Error: Confirm delete button clicked but entry ID not found."
        );
        alert(
          "An error occurred. Could not find journal entry data for deletion."
        );
        hideModal(); // Hide modal if entryId was missing
      }
    });
  } else {
    console.warn(
      "#confirm-delete-button not found. Ensure modal HTML is present."
    );
  }

  // Add event listener to the cancel delete button
  if (cancelDeleteButton) {
    cancelDeleteButton.addEventListener("click", hideModal);
  } else {
    console.warn(
      "#cancel-delete-button not found. Ensure modal HTML is present."
    );
  }

  // Initialize the delete buttons when the script loads
  initializeDeleteButtons();
});
