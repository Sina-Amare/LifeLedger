// static/js/ajax_delete.js
document.addEventListener("DOMContentLoaded", function () {
  const deleteModal = document.getElementById("delete-modal");
  const modalDialogBox = deleteModal
    ? deleteModal.querySelector(".modal-dialog-box")
    : null;
  const confirmDeleteButton = document.getElementById("confirm-delete-button");
  const cancelDeleteButton = document.getElementById("cancel-delete-button");
  const closeModalButton = document.getElementById("close-modal-x-button");
  const modalEntryTitle = document.getElementById("modal-entry-title");
  const pageModalBackdrop = document.getElementById("pageModalBackdrop");

  const translatedMessages = document.getElementById("translated-messages");
  const msgNoEntries = translatedMessages
    ? translatedMessages.querySelector("#msg-no-entries").textContent
    : "No journal entries found.";
  const msgStartWriting = translatedMessages
    ? translatedMessages.querySelector("#msg-start-writing").textContent
    : "Start by writing a new entry!";
  const msgWriteNew = translatedMessages
    ? translatedMessages.querySelector("#msg-write-new").textContent
    : "Write New Entry";
  const urlWriteNew = translatedMessages
    ? translatedMessages.querySelector("#url-write-new").textContent
    : "/journal/create/"; // Fallback, ensure this matches your actual URL if not using translated-messages div

  if (!deleteModal) {
    console.warn("Global delete modal (ID 'delete-modal') not found.");
  }
  if (!pageModalBackdrop) {
    console.warn("Page modal backdrop (ID 'pageModalBackdrop') not found.");
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

  function showModal(entryTitle, entryId, entryElementId, redirectUrlOnDelete) {
    // Added redirectUrlOnDelete
    if (!deleteModal || !confirmDeleteButton || !modalEntryTitle) {
      console.error("Core modal elements not found for showing.");
      return;
    }

    modalEntryTitle.textContent = entryTitle;
    confirmDeleteButton.dataset.entryId = entryId;
    confirmDeleteButton.dataset.entryElementId = entryElementId;
    if (redirectUrlOnDelete) {
      // Store redirect URL if provided
      confirmDeleteButton.dataset.redirectUrl = redirectUrlOnDelete;
    } else {
      confirmDeleteButton.removeAttribute("data-redirect-url");
    }

    if (pageModalBackdrop) {
      pageModalBackdrop.classList.remove("hidden");
      pageModalBackdrop.style.opacity = "1";
    }

    deleteModal.classList.remove("hidden");
    deleteModal.style.display = "flex";
    deleteModal.style.opacity = "1";
    deleteModal.style.zIndex = "50";

    if (modalDialogBox) {
      modalDialogBox.classList.remove("opacity-0", "scale-95");
      modalDialogBox.classList.add("opacity-100", "scale-100");
      modalDialogBox.style.opacity = "1";
      modalDialogBox.style.transform = "scale(1)";
    }
    console.log(
      `Modal shown for entry ID: ${entryId}, Title: ${entryTitle}, Redirect URL: ${
        redirectUrlOnDelete || "N/A"
      }`
    );
  }

  function hideModal() {
    if (pageModalBackdrop) {
      pageModalBackdrop.classList.add("hidden");
      pageModalBackdrop.style.opacity = "0";
    }
    if (!deleteModal) return;

    deleteModal.style.display = "";
    deleteModal.style.opacity = "";

    if (modalDialogBox) {
      modalDialogBox.classList.remove("opacity-100", "scale-100");
      modalDialogBox.classList.add("opacity-0", "scale-95");
      modalDialogBox.style.opacity = "";
      modalDialogBox.style.transform = "";
    }
    deleteModal.classList.remove("opacity-100");
    deleteModal.classList.add("opacity-0");

    setTimeout(() => {
      deleteModal.classList.add("hidden");
      if (confirmDeleteButton) {
        confirmDeleteButton.removeAttribute("data-entry-id");
        confirmDeleteButton.removeAttribute("data-entry-elementId");
        confirmDeleteButton.removeAttribute("data-redirect-url"); // Clear redirect URL
      }
      if (modalEntryTitle) modalEntryTitle.textContent = "";
    }, 300);
    console.log("Modal hidden.");
  }

  function initializeDeleteButtons() {
    const deleteButtons = document.querySelectorAll(".delete-entry-button");
    deleteButtons.forEach((button) => {
      button.removeEventListener("click", handleDeleteButtonClick); // Prevent multiple listeners
      button.addEventListener("click", handleDeleteButtonClick);
    });
  }

  function handleDeleteButtonClick() {
    const entryId = this.dataset.entryId;
    const entryTitle = this.dataset.entryTitle;
    const entryElementId = `entry-${entryId}`;
    const redirectUrl = this.dataset.redirectUrlOnDelete; // Get redirect URL from the clicked button

    console.log("Delete button clicked.");
    console.log("  Entry ID:", entryId);
    console.log("  Redirect URL on delete:", redirectUrl || "N/A");

    if (entryId) {
      showModal(entryTitle, entryId, entryElementId, redirectUrl);
    } else {
      console.error("Error: Could not get entry ID from delete button.");
      // Consider using a more user-friendly notification system than alert()
      // For now, keeping alert for simplicity as per original code.
      alert("An error occurred. Could not get journal entry ID.");
    }
  }

  if (confirmDeleteButton) {
    confirmDeleteButton.addEventListener("click", function () {
      const entryId = this.dataset.entryId;
      const entryElementId = this.dataset.entryElementId;
      const redirectUrlAfterDelete = this.dataset.redirectUrl; // Get stored redirect URL

      if (!entryId) {
        console.error("Error: Confirm delete clicked but entry ID not found.");
        alert("An error occurred. Entry ID missing for deletion.");
        hideModal();
        return;
      }

      const deleteUrl = `/journal/${entryId}/delete/`;
      console.log("Confirm delete. Sending POST to:", deleteUrl);

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
              `Entry ${data.entry_id || entryId} deleted successfully via AJAX.`
            );

            const currentPath = window.location.pathname;
            // Regex to check if current path is for the deleted entry's detail page
            const detailPagePattern = new RegExp(`^/journal/${entryId}/?$`);

            // ***** MODIFICATION HERE *****
            if (detailPagePattern.test(currentPath) && redirectUrlAfterDelete) {
              console.log(
                "On detail page of deleted item. Redirecting to:",
                redirectUrlAfterDelete
              );
              window.location.href = redirectUrlAfterDelete; // Perform full page redirect
            } else {
              // End of modification
              // Logic for removing element from list page (if applicable)
              const entryElement = document.getElementById(entryElementId);
              if (entryElement) {
                entryElement.style.transition =
                  "opacity 0.5s ease, transform 0.5s ease";
                entryElement.style.opacity = "0";
                entryElement.style.transform = "scale(0.95)";
                setTimeout(() => {
                  entryElement.remove();
                  console.log(
                    `Removed element with ID ${entryElementId} from list page.`
                  );
                  // Check if list is empty (if on list page)
                  const listContainer = document.querySelector(
                    ".timeline-container"
                  ); // Adjust selector if needed
                  if (listContainer && listContainer.children.length === 0) {
                    const wrapper = document.querySelector(
                      ".timeline-container-wrapper"
                    ); // Adjust selector
                    if (wrapper) {
                      wrapper.innerHTML = `
                                          <div class="text-center py-10 fade-in-element" style="animation-delay: 0.4s;">
                                              <p class="text-xl text-gray-900 dark:text-gray-100 font-medium">${msgNoEntries}</p>
                                              <p class="text-base text-gray-600 dark:text-gray-400 mt-3">${msgStartWriting}</p>
                                              <a href="${urlWriteNew}" class="write-new-button mt-8">
                                                  <i class="fas fa-feather-alt mr-1"></i>${msgWriteNew}
                                              </a>
                                          </div>`;
                    }
                  }
                }, 500);
              } else {
                console.warn(
                  `Element with ID ${entryElementId} not found for removal (might be on detail page or element ID is incorrect).`
                );
              }
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
  }
  if (closeModalButton) {
    closeModalButton.addEventListener("click", hideModal);
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

  // Observer for dynamically added content (if you have AJAX loading for list items)
  const observerTarget = document.getElementById("journal-entries-list"); // Make sure this ID exists on your list page's container
  if (observerTarget) {
    const observer = new MutationObserver((mutationsList) => {
      for (const mutation of mutationsList) {
        if (mutation.type === "childList" && mutation.addedNodes.length > 0) {
          initializeDeleteButtons(); // Re-initialize for new buttons
          break;
        }
      }
    });
    observer.observe(observerTarget, { childList: true, subtree: true });
  } else {
    console.info(
      "Observer target 'journal-entries-list' not found. Dynamic delete buttons might not work if list is AJAX loaded without re-initializing."
    );
  }
});
