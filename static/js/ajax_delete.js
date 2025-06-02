// static/js/ajax_delete.js
document.addEventListener("DOMContentLoaded", function () {
  const deleteModal = document.getElementById("delete-modal"); // Global modal from base.html
  const modalDialogBox = deleteModal
    ? deleteModal.querySelector(".modal-dialog-box")
    : null;
  const confirmDeleteButton = document.getElementById("confirm-delete-button");
  const cancelDeleteButton = document.getElementById("cancel-delete-button");
  const closeModalButton = document.getElementById("close-modal-x-button"); // 'X' close button
  const modalEntryTitle = document.getElementById("modal-entry-title");

  const pageModalBackdrop = document.getElementById("pageModalBackdrop");

  // Retrieve translated messages from DOM
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
    : "/journal/create/";

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
      pageModalBackdrop.style.opacity = "0";
    }

    if (!deleteModal) {
      console.error("Modal element not found for hiding.");
      return;
    }

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
      }
      if (modalEntryTitle) {
        modalEntryTitle.textContent = "";
      }
    }, 300); // Match duration of opacity transition
    console.log("Modal hidden.");
  }

  function initializeDeleteButtons() {
    const deleteButtons = document.querySelectorAll(".delete-entry-button");
    deleteButtons.forEach((button) => {
      // Remove existing listener to prevent multiple attachments
      button.removeEventListener("click", handleDeleteButtonClick);
      button.addEventListener("click", handleDeleteButtonClick);
    });
  }

  function handleDeleteButtonClick() {
    const entryId = this.dataset.entryId;
    const entryTitle = this.dataset.entryTitle;
    const entryElementId = `entry-${entryId}`; // ID for list or detail page element

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

      const deleteUrl = `/journal/${entryId}/delete/`; // Match your Django URL pattern
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

            // Check if current page is the detail page for the deleted entry
            const currentPath = window.location.pathname;
            const detailPagePattern = new RegExp(`^/journal/${entryId}/?$`);

            if (detailPagePattern.test(currentPath)) {
              // Redirect to journal list without full page refresh
              window.history.pushState({}, "", "/journal/");
              const wrapper = document.querySelector(
                ".timeline-container-wrapper"
              );
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
            } else {
              // Remove the element from the list page with fade-out animation
              const entryElement = document.getElementById(entryElementId);
              if (entryElement) {
                entryElement.style.transition = "opacity 0.5s ease";
                entryElement.style.opacity = "0";
                setTimeout(() => {
                  entryElement.remove();
                  console.log(`Removed element with ID ${entryElementId}.`);

                  // Check if the timeline is now empty
                  const timelineContainer = document.querySelector(
                    ".timeline-container"
                  );
                  const wrapper = document.querySelector(
                    ".timeline-container-wrapper"
                  );
                  if (
                    timelineContainer &&
                    timelineContainer.children.length === 0
                  ) {
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
                }, 500); // Duration of fade-out animation
              } else {
                console.warn(
                  `Element with ID ${entryElementId} not found for removal, but deletion successful.`
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

  // Hide modal on Escape key press
  document.addEventListener("keydown", (event) => {
    if (
      event.key === "Escape" &&
      deleteModal &&
      !deleteModal.classList.contains("hidden")
    ) {
      hideModal();
    }
  });

  // Initial call to attach event listeners to existing delete buttons
  initializeDeleteButtons();

  // Handle dynamic content addition (e.g., AJAX pagination)
  const observerTarget = document.getElementById("journal-entries-list");
  if (observerTarget) {
    const observer = new MutationObserver((mutationsList) => {
      for (const mutation of mutationsList) {
        if (mutation.type === "childList" && mutation.addedNodes.length > 0) {
          initializeDeleteButtons();
          break;
        }
      }
    });
    observer.observe(observerTarget, { childList: true, subtree: true });
  }
});
