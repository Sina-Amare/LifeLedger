document.addEventListener("DOMContentLoaded", function () {
  // --- Tag Management Logic (Your original, working code) ---
  // This entire block is preserved to ensure your tag functionality is untouched.
  const journalFormForTags = document.getElementById("journal-entry-form");
  if (journalFormForTags) {
    const hiddenTagsInputElement =
      typeof hiddenTagsInputId !== "undefined"
        ? document.getElementById(hiddenTagsInputId)
        : null;
    const suggestionButtons = document.querySelectorAll(".tag-suggestion-btn");
    const selectedTagsContainer = document.getElementById(
      "selected-tags-container"
    );

    if (hiddenTagsInputElement && selectedTagsContainer) {
      let currentSelectedTags = new Set();
      const normalizeTagName = (name) =>
        typeof name === "string" ? name.trim().toLowerCase() : "";
      const capitalizeTagName = (name) =>
        typeof name === "string"
          ? name
              .trim()
              .split(" ")
              .map(
                (word) =>
                  word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
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
  }
  // --- END of Unchanged Tag Logic ---

  // --- REWRITTEN Attachment Logic ---
  // attachmentInputId is now defined in the template's script block
  if (typeof attachmentInputId !== "undefined") {
    const attachmentsInput = document.getElementById(attachmentInputId);
    const previewGrid = document.getElementById("attachments-preview-grid");
    const addButton = document.querySelector(".attachment-add-button");

    if (!attachmentsInput || !previewGrid || !addButton) {
      console.warn(
        "Attachment UI elements not found. File upload previews will not work."
      );
    } else {
      // Listen for changes on the single file input
      attachmentsInput.addEventListener("change", function (event) {
        const files = event.target.files;
        if (!files || files.length === 0) return;

        for (const file of files) {
          if (file.type.startsWith("image/")) {
            const reader = new FileReader();
            reader.onload = (e) => {
              const previewItem = createPreviewElement(
                e.target.result,
                file.name
              );
              previewGrid.insertBefore(previewItem, addButton);
            };
            reader.readAsDataURL(file);
          }
        }
        event.target.value = ""; // Clear the input after processing
      });
    }
  }

  /**
   * Creates a DOM element for a new image preview.
   * @param {string} src - The data URL of the image.
   * @param {string} name - The name of the file for the alt text.
   * @returns {HTMLElement} - The fully constructed preview element.
   */
  function createPreviewElement(src, name) {
    const wrapper = document.createElement("div");
    wrapper.className = "attachment-preview-item group new-attachment-preview";

    const link = document.createElement("a");
    link.href = src;
    link.target = "_blank";
    link.title = `View full image: ${name}`;

    const img = document.createElement("img");
    img.src = src;
    img.alt = `Preview for ${name}`;
    img.className = "w-full h-full object-cover";

    link.appendChild(img);
    wrapper.appendChild(link);
    // NOTE: New previews don't have delete buttons to keep things simple.
    // A page refresh before saving would clear them if the user changes their mind.
    return wrapper;
  }

  // --- LOGIC FOR EXISTING ATTACHMENTS (UNCHANGED BEHAVIOR) ---
  // This adds the check/uncheck visual effect for deleting existing files.
  document
    .querySelectorAll('.existing-attachment input[type="checkbox"]')
    .forEach((checkbox) => {
      checkbox.addEventListener("change", function () {
        const parent = this.closest(".existing-attachment");
        if (parent) {
          if (this.checked) {
            parent.classList.add("marked-for-deletion");
          } else {
            parent.classList.remove("marked-for-deletion");
          }
        }
      });
    });

  // --- Full Screen Modal Logic (Your original, working code) ---
  const fullScreenModal = document.getElementById("full-screen-modal");
  if (fullScreenModal) {
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
});
