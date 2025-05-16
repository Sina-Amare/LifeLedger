// static/js/ajax_delete.js

document.addEventListener("DOMContentLoaded", function () {
  // Get modal elements - Assuming the modal HTML is present in the template
  const deleteModal = document.getElementById("delete-modal");
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
        // Does this cookie string begin with the name we want?
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
      confirmDeleteButton &&
      cancelDeleteButton &&
      modalEntryTitle
    ) {
      modalEntryTitle.textContent = entryTitle; // Set the title in the modal

      // Store the entry ID and element ID on the confirm button
      confirmDeleteButton.dataset.entryId = entryId;
      confirmDeleteButton.dataset.entryElementId = entryElementId;
      // Optionally, you could also store the delete URL here if read from the trigger button
      // const deleteButton = document.querySelector(`.delete-entry-button[data-entry-id='${entryId}']`);
      // if (deleteButton && deleteButton.dataset.deleteUrl) {
      //     confirmDeleteButton.dataset.deleteUrl = deleteButton.dataset.deleteUrl;
      // }
      deleteModal.classList.remove("hidden"); // Show the modal
      console.log(`Modal shown for entry ID: ${entryId}, Title: ${entryTitle}`);
    } else {
      console.error("Error: Delete modal elements not found in the DOM.");
    }
  }

  // Function to hide the modal
  function hideModal() {
    if (deleteModal && confirmDeleteButton) {
      deleteModal.classList.add("hidden"); // Hide the modal
      // Clear data attributes from confirm button when modal is hidden
      confirmDeleteButton.removeAttribute("data-entry-id");
      confirmDeleteButton.removeAttribute("data-entry-element-id");
      // confirmDeleteButton.removeAttribute("data-delete-url"); // Clear if you stored it
      console.log("Modal hidden.");
    }
  }

  // Add click event listener to all delete buttons with the class 'delete-entry-button'
  // This function should be called once, or use event delegation for dynamically added buttons.
  function initializeDeleteButtons() {
    const deleteButtons = document.querySelectorAll(".delete-entry-button");
    deleteButtons.forEach((button) => {
      // To prevent attaching multiple listeners if this function is called multiple times,
      // clone the node and replace it. A better approach for dynamic content is event delegation.
      const newButton = button.cloneNode(true);
      button.parentNode.replaceChild(newButton, button);

      newButton.addEventListener("click", function () {
        // Get data from the clicked button using dataset
        const entryId = this.dataset.entryId;
        const entryTitle = this.dataset.entryTitle;
        // Construct the element ID to be potentially removed from the DOM
        const entryElementId = `entry-${entryId}`;

        console.log("Delete button clicked.");
        console.log("Read entry ID from data attribute:", entryId);
        console.log("Read entry title from data attribute:", entryTitle);
        console.log("Constructed entry element ID:", entryElementId);

        if (entryId) {
          showModal(entryTitle, entryId, entryElementId);
        } else {
          console.error("Error: Could not get entry ID from delete button.");
          // TODO: Replace alert with a more user-friendly notification
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
      // Construct the delete URL dynamically using the entry ID
      // Alternative: const deleteUrl = this.dataset.deleteUrl; (if stored from trigger button)
      const deleteUrl = `/journal/${entryId}/delete/`;

      console.log("Confirm delete clicked.");
      console.log("Entry ID:", entryId);
      console.log("Element ID to remove/check:", entryElementId);
      console.log("Sending POST request to:", deleteUrl);

      if (entryId) {
        hideModal(); // Hide the modal immediately after confirmation

        fetch(deleteUrl, {
          method: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest", // Identify as Ajax request
            "X-CSRFToken": csrftoken, // Include CSRF token
            // 'Content-Type': 'application/json' // Not strictly needed for simple POST delete
          },
        })
          .then((response) => {
            console.log("Fetch response status:", response.status);
            console.log("Fetch response status text:", response.statusText);
            if (response.ok) {
              return response.json(); // We expect a JSON response from our view
            } else {
              // If response is not ok, try to read error text and throw an error
              return response.text().then((text) => {
                console.error(
                  "Server returned non-OK status:",
                  response.status,
                  response.statusText
                );
                console.error("Server response body (if any):", text);
                let errorMsg = `Server error: ${response.status} ${response.statusText}`;
                try {
                  // Try to parse as JSON in case the server sends a JSON error
                  const errorData = JSON.parse(text);
                  if (errorData && errorData.message) {
                    errorMsg = errorData.message;
                  }
                } catch (e) {
                  // If not JSON, use the raw text if it's short
                  if (text && text.length < 200 && text.indexOf("<") === -1) {
                    // Avoid showing long HTML in alert
                    errorMsg = text;
                  }
                }
                throw new Error(errorMsg); // This will be caught by the .catch() block
              });
            }
          })
          .then((data) => {
            // data should be the parsed JSON response from the server
            // Check for 'status' field with value 'success'
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
                // Check if we are on the list page by seeing if the element's parent is the list container
                if (
                  listContainer &&
                  entryElement.parentElement === listContainer
                ) {
                  // If on the list page, remove the element from the DOM
                  entryElement.remove();
                  console.log(
                    `Removed element with ID ${entryElementId} from the list.`
                  );

                  // Optional: Check if the list is now empty and show "no entries" message
                  const noEntriesMessage =
                    document.getElementById("no-entries-message");
                  if (listContainer.children.length === 0 && noEntriesMessage) {
                    noEntriesMessage.classList.remove("hidden");
                  }
                  // TODO: showNotification(data.message || "Entry deleted!", "success");
                } else {
                  // If not on the list page (e.g., on detail page), redirect to the list page
                  console.log(
                    `Not on list page or element structure changed. Redirecting to /journal/`
                  );
                  window.location.replace("/journal/"); // Or use a redirect_url from server if provided
                }
              } else {
                // If the element was not found (e.g. already removed or on detail page where full redirect is expected)
                console.log(
                  `Element with ID ${entryElementId} not found, but deletion successful. Redirecting.`
                );
                window.location.replace("/journal/");
              }
            } else {
              // If data.status is not 'success' or data is not as expected
              console.error(
                "Deletion failed based on server response:",
                data ? data.message : "Unknown server response format"
              );
              // TODO: showNotification(data && data.message ? data.message : "Failed to delete entry.", "error");
              alert(
                "Failed to delete journal entry: " +
                  (data && data.message
                    ? data.message
                    : "Server reported an issue.")
              );
            }
          })
          .catch((error) => {
            // Handle network errors or errors thrown in the .then() blocks
            console.error("Error during deletion process:", error);
            // TODO: showNotification(error.message || "An error occurred. Please try again.", "error");
            alert(
              "An error occurred while trying to delete the journal entry: " +
                error.message
            );
          });
      } else {
        console.error(
          "Error: Confirm delete button clicked but entry ID not found."
        );
        // TODO: showNotification("An error occurred. Could not find journal entry data for deletion.", "error");
        alert(
          "An error occurred. Could not find journal entry data for deletion."
        );
      }
    });
  }

  // Add event listener to the cancel delete button
  if (cancelDeleteButton) {
    cancelDeleteButton.addEventListener("click", hideModal);
  }

  // Optional: Hide modal if user clicks outside of it (on the overlay)
  // window.addEventListener('click', function(event) {
  //     if (event.target === deleteModal) {
  //         hideModal();
  //     }
  // });

  // Initialize the delete buttons when the script loads
  initializeDeleteButtons();

  // TODO: Implement a user-friendly notification system (e.g., a toast message)
  // function showNotification(message, type = 'info') {
  //     console.log(`Notification (${type}): ${message}`);
  //     // Example: Create a div, style it, append to body, then remove after a few seconds
  //     // For now, alert is used as a placeholder if you don't have one
  //     // alert(`${type.toUpperCase()}: ${message}`);
  // }
});
