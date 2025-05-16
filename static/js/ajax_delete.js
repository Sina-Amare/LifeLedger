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
      confirmDeleteButton.setAttribute("data-entry-id", entryId);
      confirmDeleteButton.setAttribute("data-entry-element-id", entryElementId);

      deleteModal.classList.remove("hidden");
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
      console.log("Modal hidden.");
    }
  }

  // Add click event listener to all delete buttons with the class 'delete-entry-button'
  // This function will be called in each template where this script is included.
  function initializeDeleteButtons() {
    const deleteButtons = document.querySelectorAll(".delete-entry-button");
    deleteButtons.forEach((button) => {
      // Remove existing listeners to prevent duplicates if called multiple times
      // This is a simple approach; for more complex apps, consider event delegation
      const old_element = button;
      const new_element = old_element.cloneNode(true);
      old_element.parentNode.replaceChild(new_element, old_element);

      new_element.addEventListener("click", function () {
        // Get data from the clicked button
        const entryId = this.getAttribute("data-entry-id");
        const entryTitle = this.getAttribute("data-entry-title");
        // The element to remove might be the parent card, not the button itself
        // We need a way to identify the main container element for the entry
        // Let's assume the main container has an ID like 'entry-{{ entry.pk }}'
        const entryElementId = `entry-${entryId}`; // Construct the element ID

        console.log("Delete button clicked.");
        console.log("Read entry ID from data attribute:", entryId);
        console.log("Read entry title from data attribute:", entryTitle);
        console.log("Constructed entry element ID:", entryElementId);

        // Check if entryId is valid before showing modal
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
  // This listener is added once when the script loads
  if (confirmDeleteButton) {
    confirmDeleteButton.addEventListener("click", function () {
      // Get data from the confirm button's data attributes
      const entryId = this.getAttribute("data-entry-id");
      const entryElementId = this.getAttribute("data-entry-element-id");
      const entryElement = document.getElementById(entryElementId);

      if (entryId && entryElement) {
        // Hide the modal immediately after confirmation
        hideModal();

        // Construct the delete URL dynamically using the entry ID
        const deleteUrl = `/journal/${entryId}/delete/`; // Construct URL here

        console.log("Confirm delete clicked.");
        console.log("Sending POST request to:", deleteUrl); // Method is POST

        // Send the Ajax request using the constructed URL
        fetch(deleteUrl, {
          method: "POST", // Send as POST request to match Django view
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
              // Try to parse JSON, but handle cases where it might not be JSON
              return response.text().then((text) => {
                try {
                  return JSON.parse(text);
                } catch (e) {
                  console.warn(
                    "Received non-JSON response, but status is OK:",
                    text
                  );
                  // If status is OK but not JSON, assume success if needed, or log a warning
                  // For deletion, we expect a JSON response, so throwing an error is safer
                  throw new Error(
                    "Expected JSON response, but received non-JSON."
                  );
                }
              });
            } else {
              // If response is not ok, read the response body and throw an error
              return response.text().then((text) => {
                console.error(
                  "Server returned non-OK status:",
                  response.status,
                  response.statusText
                );
                console.error("Server response body:", text);
                throw new Error(
                  `Server error: ${response.status} ${response.statusText}`
                );
              });
            }
          })
          .then((data) => {
            // Handle the JSON response from the server
            if (data.success) {
              console.log(
                `Journal entry ${data.entry_id} deleted successfully.`
              );

              // --- Start: Logic to handle redirect on detail page vs removing element on list page ---
              // Check if the deleted element's parent is the list container
              const listContainer = document.getElementById(
                "journal-entries-list"
              );
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
              } else {
                // If not on the list page (likely detail page), redirect to the list page
                console.log(`Not on list page. Redirecting to /journal/`);
                // Use window.location.replace to prevent going back to the deleted entry page
                window.location.replace("/journal/"); // Redirect to the journal list page
              }
              // --- End: Logic to handle redirect ---

              // TODO: Add a success message notification (optional, maybe a temporary div)
            } else {
              // Deletion failed based on server-side logic
              console.error(
                "Deletion failed:",
                data.message || "Server reported failure"
              );
              alert(
                "Failed to delete journal entry: " +
                  (data.message || "Unknown server error")
              );
            }
          })
          .catch((error) => {
            // Handle any network errors or errors thrown in the .then block
            console.error("Error during deletion:", error);
            alert(
              "An error occurred while trying to delete the journal entry. Check console for details."
            );
          });
      } else {
        console.error(
          "Error: Confirm delete button clicked but entry ID or element not found."
        );
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

  // Optional: Hide modal if user clicks outside of it
  // window.addEventListener('click', function(event) {
  //     if (event.target === deleteModal) {
  //         hideModal();
  //     }
  // });

  // Initialize the delete buttons when the script loads
  initializeDeleteButtons();
});
