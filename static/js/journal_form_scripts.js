// static/js/journal_form_scripts.js
document.addEventListener("DOMContentLoaded", function () {
  const journalFormForTags = document.getElementById("journal-entry-form");
  const hiddenTagsInputElement =
    typeof hiddenTagsInputId !== "undefined"
      ? document.getElementById(hiddenTagsInputId)
      : null;
  const suggestionButtons = document.querySelectorAll(".tag-suggestion-btn");
  const selectedTagsContainer = document.getElementById(
    "selected-tags-container"
  );

  if (!journalFormForTags) {
    console.error("CRITICAL: Journal form ('journal-entry-form') not found.");
  }
  if (!hiddenTagsInputElement) {
    console.error(
      "CRITICAL: Hidden input field for tags was not found using ID:",
      typeof hiddenTagsInputId !== "undefined"
        ? hiddenTagsInputId
        : "hiddenTagsInputId_not_defined_in_template"
    );
  }
  if (!selectedTagsContainer) {
    console.error(
      "CRITICAL: Container for selected tag pills ('selected-tags-container') was not found."
    );
  }
  if (suggestionButtons.length === 0) {
    console.warn("No tag suggestion buttons (.tag-suggestion-btn) found.");
  }

  let currentSelectedTags = new Set(); // Stores normalized (lowercase) tag names

  function normalizeTagName(name) {
    return typeof name === "string" ? name.trim().toLowerCase() : "";
  }

  function capitalizeTagName(name) {
    return typeof name === "string"
      ? name
          .trim()
          .split(" ")
          .map(
            (word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
          )
          .join(" ")
      : "";
  }

  window.updatePillsAndHiddenInput = function () {
    if (!hiddenTagsInputElement || !selectedTagsContainer) {
      console.error(
        "updatePillsAndHiddenInput: Missing critical elements (hidden input or tags container). Aborting update."
      );
      return;
    }

    // 1. Update Hidden Input: Based *only* on currentSelectedTags
    const capitalizedTagsForSubmit = Array.from(currentSelectedTags)
      .map((normalizedTagName) => capitalizeTagName(normalizedTagName))
      .filter((tag) => tag); // Ensure no empty strings

    hiddenTagsInputElement.value = capitalizedTagsForSubmit.join(", ");
    console.log(
      "JS: Hidden input value updated to:",
      `"${hiddenTagsInputElement.value}"`,
      `(From currentSelectedTags: ${JSON.stringify(
        Array.from(currentSelectedTags)
      )})`
    );

    // 2. Update Visual Pills: Clear and re-render based *only* on currentSelectedTags
    selectedTagsContainer.innerHTML = ""; // Clear all existing pills

    currentSelectedTags.forEach((normalizedTagName) => {
      const displayTagName = capitalizeTagName(normalizedTagName);
      if (!displayTagName) return;

      const pill = document.createElement("span");
      let emojiPrefix = "";

      const predefinedTagButton = Array.from(suggestionButtons).find(
        (btn) => normalizeTagName(btn.dataset.tagName) === normalizedTagName
      );
      if (predefinedTagButton && predefinedTagButton.dataset.tagEmoji) {
        emojiPrefix = predefinedTagButton.dataset.tagEmoji + " ";
      }

      pill.className =
        "selected-tag-pill inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-primary-light/20 text-primary-dark dark:bg-primary-dark/30 dark:text-primary-light shadow-sm transition-all duration-200 hover:shadow-md";
      pill.dataset.tagName = displayTagName; // Store capitalized version for consistency, but logic uses normalized

      const textNode = document.createElement("span");
      textNode.textContent = emojiPrefix + displayTagName;
      pill.appendChild(textNode);

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.innerHTML = "&times;"; // Use &times; for a nicer 'x'
      removeBtn.className =
        "remove-tag-btn ml-2 -mr-0.5 p-0.5 rounded-full inline-flex items-center justify-center text-primary-dark/70 dark:text-primary-light/70 hover:bg-primary-dark/20 dark:hover:bg-primary-light/20 focus:outline-none focus:ring-2 focus:ring-primary-dark dark:focus:ring-primary-light";
      removeBtn.setAttribute("aria-label", `Remove ${displayTagName}`);

      removeBtn.onclick = function (event) {
        event.stopPropagation();
        console.log("JS: Removing tag:", normalizedTagName);
        currentSelectedTags.delete(normalizedTagName);
        updatePillsAndHiddenInput(); // Re-render
      };
      pill.appendChild(removeBtn);
      selectedTagsContainer.appendChild(pill);
    });
    console.log(
      "JS: Pills updated. currentSelectedTags:",
      JSON.stringify(Array.from(currentSelectedTags))
    );
  };

  // Initialize tags from Django context if available
  if (
    typeof initialTagsFromDjango !== "undefined" &&
    initialTagsFromDjango.trim() !== ""
  ) {
    console.log(
      "JS: Initializing tags from Django:",
      `"${initialTagsFromDjango}"`
    );
    initialTagsFromDjango
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t.length > 0)
      .forEach((capitalizedTagName) => {
        const normalized = normalizeTagName(capitalizedTagName);
        if (normalized) {
          // Ensure not adding empty normalized tags
          currentSelectedTags.add(normalized);
        }
      });
  } else {
    console.log("JS: No initial tags from Django or it's empty.");
  }
  // Always call updatePillsAndHiddenInput after initialization to set up UI and hidden field correctly
  updatePillsAndHiddenInput();

  suggestionButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const tagNameFromButton = this.dataset.tagName; // This is capitalized
      const normalizedName = normalizeTagName(tagNameFromButton);
      if (!normalizedName) return; // Should not happen if data-tag-name is always set

      console.log(
        "JS: Suggestion button clicked for:",
        tagNameFromButton,
        "(Normalized:",
        normalizedName + ")"
      );

      if (currentSelectedTags.has(normalizedName)) {
        console.log(
          "JS: Deleting tag from currentSelectedTags:",
          normalizedName
        );
        currentSelectedTags.delete(normalizedName);
      } else {
        console.log("JS: Adding tag to currentSelectedTags:", normalizedName);
        currentSelectedTags.add(normalizedName);
      }
      updatePillsAndHiddenInput();
    });
  });

  if (journalFormForTags) {
    journalFormForTags.addEventListener("submit", function (event) {
      console.log(
        "JS: Form submit event triggered. Ensuring hidden tags input is up-to-date."
      );
      if (typeof window.updatePillsAndHiddenInput === "function") {
        window.updatePillsAndHiddenInput(); // Final update before any submission type
      }
      // The actual AJAX submission is handled by journal_form_ai_progress.js, which also calls this.
      // This listener is an additional safeguard.
    });
  }

  // --- File Preview Logic (largely unchanged from your provided code, with minor safety checks) ---
  window.handleFilePreview = function (input) {
    const previewContainerId = `preview-${input.id}`;
    const previewContainer = document.getElementById(previewContainerId);
    if (!previewContainer) {
      console.error(
        `Preview container not found for input ID: ${previewContainerId}`
      );
      return;
    }

    // Initialize or retrieve the list of all files for this input
    let allFiles = [];
    try {
      allFiles = input.dataset.allFiles
        ? JSON.parse(input.dataset.allFiles)
        : [];
    } catch (e) {
      console.error("Error parsing input.dataset.allFiles:", e);
      allFiles = []; // Reset to empty array on error
    }

    const newFilesFromInput = Array.from(input.files || []);

    // Add newly selected files to our 'allFiles' array, avoiding duplicates
    newFilesFromInput.forEach((file) => {
      const fileExists = allFiles.some(
        (f) =>
          f.name === file.name && f.size === file.size && f.type === file.type
      );
      if (!fileExists) {
        allFiles.push({
          name: file.name,
          size: file.size,
          type: file.type,
          // dataURL will be populated for images by the FileReader
          // We need to store the actual File object temporarily if we want to read it
          transientFileObject: file, // Store the actual file object for FileReader
        });
      }
    });

    // Update the input's data attribute with the stringified list of all files
    input.dataset.allFiles = JSON.stringify(
      allFiles.map((f) => ({
        name: f.name,
        size: f.size,
        type: f.type,
        dataURL: f.dataURL /* no transientFileObject here */,
      }))
    );

    // Clear and rebuild preview
    previewContainer.innerHTML = "";

    allFiles.forEach((fileInfo, index) => {
      const previewItem = document.createElement("div");
      previewItem.className =
        "preview-item relative group border border-gray-200 dark:border-gray-700 rounded-lg p-2 flex flex-col items-center text-center";

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className =
        "remove-preview-btn absolute top-1 right-1 bg-red-500 text-white rounded-full h-5 w-5 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-xs leading-none";
      removeBtn.innerHTML = "&times;";
      removeBtn.setAttribute("aria-label", `Remove ${fileInfo.name}`);
      removeBtn.onclick = function (event) {
        event.stopPropagation();
        allFiles.splice(index, 1);
        input.dataset.allFiles = JSON.stringify(
          allFiles.map((f) => ({
            name: f.name,
            size: f.size,
            type: f.type,
            dataURL: f.dataURL,
          }))
        );

        // Reconstruct input.files for submission (this is the tricky part)
        // We need to create a new DataTransfer object and add remaining files to it.
        // This requires having access to the original File objects.
        // For now, this example won't perfectly reconstruct input.files for removal.
        // A more robust file management strategy would be needed for that.
        handleFilePreview(input); // Re-render previews
      };

      const fileType = fileInfo.type ? fileInfo.type.toLowerCase() : "";
      const isImage = fileType.startsWith("image/");

      if (isImage) {
        const img = document.createElement("img");
        img.alt = fileInfo.name || "Image Preview";
        img.className =
          "max-w-full h-32 rounded-md object-contain bg-gray-100 dark:bg-gray-700 cursor-pointer mb-1";
        img.onclick = function () {
          if (img.src && !img.src.startsWith("data:image/gif"))
            showFullScreenImage(img.src);
        };

        if (fileInfo.dataURL) {
          // Image already has dataURL
          img.src = fileInfo.dataURL;
          previewItem.appendChild(img);
        } else if (fileInfo.transientFileObject) {
          // New image, needs to be read
          const placeholder = document.createElement("div");
          placeholder.className =
            "w-full h-32 bg-gray-200 dark:bg-gray-700 rounded-md flex items-center justify-center text-gray-500 text-xs mb-1";
          placeholder.textContent = "Loading...";
          previewItem.appendChild(placeholder);

          const reader = new FileReader();
          reader.onload = function (e) {
            fileInfo.dataURL = e.target.result; // Cache it in our allFiles structure
            img.src = e.target.result;
            if (previewItem.contains(placeholder)) {
              previewItem.replaceChild(img, placeholder);
            } else {
              // Should not happen if placeholder was added
              previewItem.insertBefore(img, previewItem.firstChild);
            }
            // Update dataset.allFiles again because dataURL has been populated
            input.dataset.allFiles = JSON.stringify(
              allFiles.map((f) => ({
                name: f.name,
                size: f.size,
                type: f.type,
                dataURL: f.dataURL,
              }))
            );
          };
          reader.onerror = function () {
            if (previewItem.contains(placeholder)) {
              placeholder.textContent = "Preview error";
            }
          };
          reader.readAsDataURL(fileInfo.transientFileObject);
          // Remove transientFileObject after attempting to read, it's not needed for JSON.stringify
          delete fileInfo.transientFileObject;
        } else {
          // No dataURL and no file object (e.g. from initial load without pre-generated dataURLs)
          const fileInfoDiv = document.createElement("div");
          fileInfoDiv.className =
            "w-full h-32 bg-gray-200 dark:bg-gray-700 rounded-md flex items-center justify-center text-gray-500 text-xs mb-1";
          fileInfoDiv.innerHTML = `<i class="fas fa-image text-2xl text-gray-400"></i>`;
          previewItem.appendChild(fileInfoDiv);
        }
      } else {
        // Non-image files
        const fileInfoDiv = document.createElement("div");
        fileInfoDiv.className =
          "w-full h-32 bg-gray-100 dark:bg-gray-800 rounded-md flex flex-col items-center justify-center text-sm p-2 mb-1";
        let iconClass = "fas fa-file-alt text-3xl";
        if (fileType.startsWith("audio/"))
          iconClass = "fas fa-file-audio text-3xl";
        if (fileType.startsWith("video/"))
          iconClass = "fas fa-file-video text-3xl";
        if (fileType.startsWith("application/pdf"))
          iconClass = "fas fa-file-pdf text-3xl";
        fileInfoDiv.innerHTML = `<i class="${iconClass} text-gray-500 dark:text-gray-400 mb-2"></i> <span class="truncate block w-full text-center">${fileInfo.name}</span>`;
        previewItem.appendChild(fileInfoDiv);
      }
      previewItem.appendChild(removeBtn);
      selectedTagsContainer.insertAdjacentElement("afterend", previewItem); // Place previews after tags
    });
    // After processing new files, clear the actual file input to prevent re-processing on next change event if not desired
    input.value = ""; // This clears the <input type="file"> selection
  };

  const fullScreenModal = document.getElementById("full-screen-modal");
  const fullScreenImage = document.getElementById("full-screen-image");
  const closeBtn = fullScreenModal
    ? fullScreenModal.querySelector(".close-btn")
    : null;

  window.showFullScreenImage = function (src) {
    if (
      fullScreenImage &&
      fullScreenModal &&
      src &&
      !src.startsWith("data:image/gif")
    ) {
      fullScreenImage.src = src;
      fullScreenModal.style.display = "flex";
    }
  };

  if (closeBtn && fullScreenModal) {
    closeBtn.addEventListener("click", function () {
      fullScreenModal.style.display = "none";
      if (fullScreenImage) fullScreenImage.src = "";
    });
  }
  if (fullScreenModal) {
    fullScreenModal.addEventListener("click", function (event) {
      if (event.target === fullScreenModal) {
        fullScreenModal.style.display = "none";
        if (fullScreenImage) fullScreenImage.src = "";
      }
    });
  }
});
