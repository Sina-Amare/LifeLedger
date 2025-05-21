document.addEventListener("DOMContentLoaded", function () {
  const journalFormForTags = document.getElementById("journal-entry-form");
  const hiddenTagsInput = document.getElementById(
    "{{ form.tags.id_for_label }}"
  );
  const suggestionButtons = document.querySelectorAll(".tag-suggestion-btn");
  const selectedTagsContainer = document.getElementById(
    "selected-tags-container"
  );

  let currentSelectedTags = new Set();

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
    const capitalizedTagsForSubmit = Array.from(currentSelectedTags).map(
      (t_norm) => capitalizeTagName(t_norm)
    );
    if (hiddenTagsInput) {
      hiddenTagsInput.value = capitalizedTagsForSubmit.join(", ");
    }

    if (selectedTagsContainer) {
      selectedTagsContainer.innerHTML = "";
      capitalizedTagsForSubmit.forEach((displayTagName, index) => {
        if (!displayTagName) return;
        const normalizedTagName = normalizeTagName(displayTagName);
        const pill = document.createElement("span");
        let emojiPrefix = "";

        const predefinedTagButton = Array.from(suggestionButtons).find(
          (btn) => normalizeTagName(btn.dataset.tagName) === normalizedTagName
        );
        if (predefinedTagButton && predefinedTagButton.dataset.tagEmoji) {
          emojiPrefix = predefinedTagButton.dataset.tagEmoji + " ";
        }

        pill.className = "selected-tag-pill";
        pill.textContent = emojiPrefix + displayTagName;

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.innerHTML = "×";
        removeBtn.className = "remove-tag-btn";
        removeBtn.setAttribute("aria-label", `Remove ${displayTagName}`);
        removeBtn.onclick = function (event) {
          event.stopPropagation();
          currentSelectedTags.delete(normalizedTagName);
          updatePillsAndHiddenInput();
        };
        pill.appendChild(removeBtn);

        // Add animation
        setTimeout(() => {
          pill.classList.add("active");
        }, index * 100); // Delay for each pill to create a staggered effect

        selectedTagsContainer.appendChild(pill);
      });
    }
  };

  const initialTagsFromDjango =
    "{{ initial_tags_str|escapejs|default_if_none:'' }}";
  if (initialTagsFromDjango) {
    initialTagsFromDjango
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t.length > 0)
      .forEach((t) => currentSelectedTags.add(normalizeTagName(t)));
    updatePillsAndHiddenInput();
  }

  suggestionButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const tagNameFromButton = this.dataset.tagName;
      const normalizedName = normalizeTagName(tagNameFromButton);

      if (currentSelectedTags.has(normalizedName)) {
        currentSelectedTags.delete(normalizedName);
      } else {
        currentSelectedTags.add(normalizedName);
      }
      updatePillsAndHiddenInput();
    });
  });

  // Handle file preview with multiple files and removal
  window.handleFilePreview = function (input) {
    const previewContainer = document.getElementById(`preview-${input.id}`);
    const dataTransfer = new DataTransfer();

    // Initialize allFiles for this input if it doesn't exist
    if (!input.dataset.allFiles) {
      input.dataset.allFiles = JSON.stringify([]);
    }

    // Load existing files
    let allFiles = JSON.parse(input.dataset.allFiles);

    // Add new files
    if (input.files && input.files.length > 0) {
      Array.from(input.files).forEach((file) => {
        const fileExists = allFiles.some(
          (f) => f.name === file.name && f.size === file.size
        );
        if (!fileExists) {
          allFiles.push({
            name: file.name,
            size: file.size,
            type: file.type,
            dataURL: null, // Will be populated for images
          });
          dataTransfer.items.add(file);
        }
      });
    }

    // Update input.files with all files
    input.files = dataTransfer.files;
    input.dataset.allFiles = JSON.stringify(allFiles);

    // Clear and rebuild preview
    previewContainer.innerHTML = "";

    allFiles.forEach((fileInfo, index) => {
      const fileType = fileInfo.type.toLowerCase();
      const isImage = fileType.includes("image");
      const previewItem = document.createElement("div");
      previewItem.className = "preview-item";

      if (isImage) {
        // If dataURL is already available, use it
        if (fileInfo.dataURL) {
          const img = document.createElement("img");
          img.src = fileInfo.dataURL;
          img.alt = "New File Preview";
          img.className =
            "max-w-full sm:max-w-[250px] max-h-40 rounded-xl border dark:border-gray-600 object-contain bg-gray-100 dark:bg-gray-700 p-1";
          img.onclick = function () {
            showFullScreenImage(fileInfo.dataURL);
          };

          const removeBtn = document.createElement("button");
          removeBtn.className = "remove-preview-btn";
          removeBtn.innerHTML = "×";
          removeBtn.onclick = function (event) {
            event.stopPropagation();
            allFiles.splice(index, 1); // Remove file from allFiles
            input.dataset.allFiles = JSON.stringify(allFiles);
            handleFilePreview(input); // Recreate preview
          };

          previewItem.appendChild(img);
          previewItem.appendChild(removeBtn);
          previewContainer.appendChild(previewItem);
        } else {
          // Read the file to get dataURL
          const file = Array.from(input.files).find(
            (f) => f.name === fileInfo.name && f.size === fileInfo.size
          );
          if (file) {
            const reader = new FileReader();
            reader.onload = function (e) {
              fileInfo.dataURL = e.target.result;
              input.dataset.allFiles = JSON.stringify(allFiles);

              const img = document.createElement("img");
              img.src = e.target.result;
              img.alt = "New File Preview";
              img.className =
                "max-w-full sm:max-w-[250px] max-h-40 rounded-xl border dark:border-gray-600 object-contain bg-gray-100 dark:bg-gray-700 p-1";
              img.onclick = function () {
                showFullScreenImage(e.target.result);
              };

              const removeBtn = document.createElement("button");
              removeBtn.className = "remove-preview-btn";
              removeBtn.innerHTML = "×";
              removeBtn.onclick = function (event) {
                event.stopPropagation();
                allFiles.splice(index, 1); // Remove file from allFiles
                input.dataset.allFiles = JSON.stringify(allFiles);
                handleFilePreview(input); // Recreate preview
              };

              previewItem.appendChild(img);
              previewItem.appendChild(removeBtn);
              previewContainer.appendChild(previewItem);
            };
            reader.readAsDataURL(file);
          }
        }
      } else {
        const fileInfoDiv = document.createElement("div");
        fileInfoDiv.className =
          "flex items-center space-x-3 p-3 bg-gray-100 dark:bg-gray-800 rounded-xl";
        fileInfoDiv.innerHTML = `
                    <i class="fas fa-paperclip text-gray-500 dark:text-gray-400"></i>
                    <span class="text-sm text-primary-light dark:text-primary-dark break-all">${fileInfo.name}</span>
                `;
        const removeBtn = document.createElement("button");
        removeBtn.className = "remove-preview-btn";
        removeBtn.innerHTML = "×";
        removeBtn.onclick = function (event) {
          event.stopPropagation();
          allFiles.splice(index, 1); // Remove file from allFiles
          input.dataset.allFiles = JSON.stringify(allFiles);
          handleFilePreview(input); // Recreate preview
        };
        previewItem.appendChild(fileInfoDiv);
        previewItem.appendChild(removeBtn);
        previewContainer.appendChild(previewItem);
      }
    });
  };

  // Full-screen image modal
  const fullScreenModal = document.getElementById("full-screen-modal");
  const fullScreenImage = document.getElementById("full-screen-image");
  const closeBtn = document.querySelector(".close-btn");

  window.showFullScreenImage = function (src) {
    fullScreenImage.src = src;
    fullScreenModal.style.display = "flex";
  };

  closeBtn.addEventListener("click", function () {
    fullScreenModal.style.display = "none";
    fullScreenImage.src = "";
  });

  fullScreenModal.addEventListener("click", function (event) {
    if (event.target === fullScreenModal) {
      fullScreenModal.style.display = "none";
      fullScreenImage.src = "";
    }
  });
});
