/**
 * Main entry point for all scripts on the journal form page.
 * This function is executed when the DOM is fully loaded and initializes all interactive components.
 */
document.addEventListener("DOMContentLoaded", function () {
  // --- Tag Management Logic ---
  // Unchanged from your original code.
  initializeTagManagement();

  // --- Attachment Previews for New Uploads ---
  // Rewritten for clarity and correctness.
  initializeNewAttachmentPreviews();

  // --- Visual Feedback for Deleting Existing Attachments ---
  // Unchanged from your original code.
  initializeExistingAttachmentDeletion();

  // --- Full Screen Image Modal ---
  // Unchanged from your original code.
  initializeFullScreenModal();
});

/**
 * Handles the setup of the tag selection UI, including suggestions and pill creation.
 * This function is preserved from your original script.
 */
function initializeTagManagement() {
  const journalFormForTags = document.getElementById("journal-entry-form");
  if (!journalFormForTags) return;

  // These variables are expected to be defined in a <script> tag in the HTML template.
  if (typeof hiddenTagsInputId === "undefined") {
    console.warn("`hiddenTagsInputId` is not defined. Tagging will not work.");
    return;
  }

  const hiddenTagsInputElement = document.getElementById(hiddenTagsInputId);
  const suggestionButtons = document.querySelectorAll(".tag-suggestion-btn");
  const selectedTagsContainer = document.getElementById(
    "selected-tags-container"
  );

  if (!hiddenTagsInputElement || !selectedTagsContainer) {
    console.warn(
      "Tagging UI elements not found, functionality will be disabled."
    );
    return;
  }

  let currentSelectedTags = new Set();
  const normalizeTagName = (name) =>
    typeof name === "string" ? name.trim().toLowerCase() : "";
  const capitalizeTagName = (name) =>
    typeof name === "string"
      ? name
          .trim()
          .split(" ")
          .map(
            (word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
          )
          .join(" ")
      : "";

  window.updatePillsAndHiddenInput = function () {
    const capitalizedTagsForSubmit = Array.from(currentSelectedTags)
      .map(capitalizeTagName)
      .filter(Boolean);
    hiddenTagsInputElement.value = capitalizedTagsForSubmit.join(", ");
    selectedTagsContainer.innerHTML = "";

    currentSelectedTags.forEach((normalizedTagName) => {
      const displayTagName = capitalizeTagName(normalizedTagName);
      if (!displayTagName) return;

      const pill = document.createElement("span");
      const predefinedTagButton = Array.from(suggestionButtons).find(
        (btn) => normalizeTagName(btn.dataset.tagName) === normalizedTagName
      );
      const emojiPrefix = predefinedTagButton?.dataset.tagEmoji
        ? `${predefinedTagButton.dataset.tagEmoji} `
        : "";

      pill.className =
        "selected-tag-pill inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-primary-light/20 text-primary-dark dark:bg-primary-dark/30 dark:text-primary-light shadow-sm transition-all duration-200 hover:shadow-md";
      pill.innerHTML = `<span>${emojiPrefix}${displayTagName}</span><button type="button" class="remove-tag-btn ml-2 -mr-0.5 p-0.5 rounded-full inline-flex items-center justify-center text-primary-dark/70 dark:text-primary-light/70 hover:bg-primary-dark/20 dark:hover:bg-primary-light/20">&times;</button>`;

      pill.querySelector(".remove-tag-btn").onclick = (event) => {
        event.stopPropagation();
        currentSelectedTags.delete(normalizedTagName);
        updatePillsAndHiddenInput();
      };
      selectedTagsContainer.appendChild(pill);
    });
  };

  if (
    typeof initialTagsFromDjango !== "undefined" &&
    initialTagsFromDjango.trim()
  ) {
    initialTagsFromDjango
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean)
      .forEach((t) => currentSelectedTags.add(normalizeTagName(t)));
  }
  updatePillsAndHiddenInput();

  suggestionButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const normalizedName = normalizeTagName(this.dataset.tagName);
      if (!normalizedName) return;
      currentSelectedTags.has(normalizedName)
        ? currentSelectedTags.delete(normalizedName)
        : currentSelectedTags.add(normalizedName);
      updatePillsAndHiddenInput();
    });
  });
}

/**
 * Manages the logic for new file attachments, including cumulative selection and previews with remove buttons.
 * Uses a DataTransfer object to programmatically manage the file list, allowing for adding and removing files before submission.
 */
function initializeNewAttachmentPreviews() {
  // `newAttachmentsInputId` is defined in a script tag in the template from Django context.
  if (typeof newAttachmentsInputId === "undefined") return;

  const attachmentsInput = document.getElementById(newAttachmentsInputId);
  const previewGrid = document.getElementById("attachments-preview-grid");

  if (!attachmentsInput || !previewGrid) {
    console.warn(
      "New attachment input or preview grid not found. Preview functionality will be disabled."
    );
    return;
  }

  // This DataTransfer object is the key to managing a file list programmatically.
  const dataTransfer = new DataTransfer();

  attachmentsInput.addEventListener("change", function (event) {
    // Add the newly selected files to our persistent DataTransfer object.
    for (const file of event.target.files) {
      dataTransfer.items.add(file);
    }

    // Update the actual input's file list with our aggregated list.
    attachmentsInput.files = dataTransfer.files;

    // Re-render all previews based on the updated file list.
    renderPreviews();
  });

  /**
   * Renders image previews in the grid. It clears previous previews and regenerates them
   * from the files currently in the DataTransfer object.
   */
  function renderPreviews() {
    previewGrid.innerHTML = ""; // Clear existing previews to avoid duplication.

    Array.from(attachmentsInput.files).forEach((file, index) => {
      if (file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = (e) => {
          const previewItem = createPreviewElement(
            e.target.result,
            file.name,
            index
          );
          previewGrid.appendChild(previewItem);
        };
        reader.readAsDataURL(file);
      }
    });
  }

  /**
   * Creates a single preview element for an image, including the image itself and a remove button.
   * @param {string} src - The data URL for the image preview.
   * @param {string} name - The name of the file for the alt text.
   * @param {number} index - The file's index in the FileList, crucial for the remove functionality.
   * @returns {HTMLElement} The complete DOM element for the preview item.
   */
  function createPreviewElement(src, name, index) {
    const wrapper = document.createElement("div");
    wrapper.className = "relative group attachment-preview-item";

    const img = document.createElement("img");
    img.src = src;
    img.alt = `Preview for ${name}`;
    img.className =
      "w-full h-32 object-cover rounded-lg shadow-md border-2 border-transparent group-hover:border-primary-light dark:group-hover:border-primary-dark transition-all duration-200 cursor-pointer";
    img.onclick = () => showFullScreenImage(src);

    const removeBtn = document.createElement("button");
    removeBtn.type = "button"; // Important to prevent form submission.
    removeBtn.innerHTML = "&times;";
    removeBtn.className =
      "absolute top-1 right-1 bg-red-500 text-white rounded-full h-6 w-6 flex items-center justify-center text-lg font-bold opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-700";
    removeBtn.title = "Remove this file";
    removeBtn.onclick = (e) => {
      e.stopPropagation(); // Prevent the image click event (full screen) from firing.
      removeFile(index);
    };

    wrapper.appendChild(img);
    wrapper.appendChild(removeBtn);
    return wrapper;
  }

  /**
   * Removes a file from the DataTransfer object and the input element, then re-renders the previews.
   * @param {number} indexToRemove - The index of the file to be removed.
   */
  function removeFile(indexToRemove) {
    // Create a new DataTransfer object and add all files except the one at the specified index.
    const newFiles = new DataTransfer();
    const currentFiles = attachmentsInput.files;
    for (let i = 0; i < currentFiles.length; i++) {
      if (i !== indexToRemove) {
        newFiles.items.add(currentFiles[i]);
      }
    }

    // Update the input element with the new file list.
    attachmentsInput.files = newFiles.files;

    // Critically, also update the main DataTransfer object to reflect the change.
    dataTransfer.items.clear();
    for (const file of newFiles.files) {
      dataTransfer.items.add(file);
    }

    // Finally, re-render the previews to show the updated selection.
    renderPreviews();
  }
}

/**
 * Adds a visual style to existing attachments that are marked for deletion.
 * This function is preserved from your original script.
 */
function initializeExistingAttachmentDeletion() {
  document
    .querySelectorAll('.existing-attachment-item input[type="checkbox"]')
    .forEach((checkbox) => {
      checkbox.addEventListener("change", function () {
        const parent = this.closest(".existing-attachment-item");
        if (parent) {
          parent.classList.toggle("marked-for-deletion", this.checked);
        }
      });
    });
}

/**
 * Sets up the modal for viewing images in full screen.
 * This function is preserved from your original script.
 */
function initializeFullScreenModal() {
  const fullScreenModal = document.getElementById("full-screen-modal");
  if (!fullScreenModal) return;

  const fullScreenImage = document.getElementById("full-screen-image");
  const closeBtn = fullScreenModal.querySelector(".close-btn");

  window.showFullScreenImage = function (src) {
    if (fullScreenImage && src && !src.startsWith("data:image/gif")) {
      fullScreenImage.src = src;
      fullScreenModal.style.display = "flex";
    }
  };

  if (closeBtn) {
    closeBtn.addEventListener("click", function () {
      fullScreenModal.style.display = "none";
      if (fullScreenImage) fullScreenImage.src = "";
    });
  }

  fullScreenModal.addEventListener("click", function (event) {
    if (event.target === fullScreenModal) {
      fullScreenModal.style.display = "none";
      if (fullScreenImage) fullScreenImage.src = "";
    }
  });
}
