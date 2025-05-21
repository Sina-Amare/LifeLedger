document.addEventListener("DOMContentLoaded", function () {
  const journalFormForTags = document.getElementById("journal-entry-form");
  const hiddenTagsInput = document.getElementById(
    "{{ form.tags.id_for_label }}"
  );
  const displayTagsInput = document.getElementById("tags-display-input");
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
      capitalizedTagsForSubmit.forEach((displayTagName) => {
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
      if (displayTagsInput) {
        displayTagsInput.value = "";
        displayTagsInput.focus();
      }
    });
  });

  if (displayTagsInput) {
    displayTagsInput.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === ",") {
        event.preventDefault();
        const newTagNameRaw = this.value.trim().replace(/,$/, "").trim();
        if (newTagNameRaw) {
          const normalizedNewTag = normalizeTagName(newTagNameRaw);
          currentSelectedTags.add(normalizedNewTag);
          updatePillsAndHiddenInput();
        }
        this.value = "";
      }
    });
    displayTagsInput.addEventListener("blur", function () {
      setTimeout(() => {
        const newTagNameRaw = this.value.trim().replace(/,$/, "").trim();
        if (newTagNameRaw) {
          const normalizedNewTag = normalizeTagName(newTagNameRaw);
          if (!currentSelectedTags.has(normalizedNewTag)) {
            currentSelectedTags.add(normalizedNewTag);
            updatePillsAndHiddenInput();
          }
          if (
            document.activeElement !== this &&
            !Array.from(suggestionButtons).some(
              (btn) => btn === document.activeElement
            )
          ) {
            this.value = "";
          }
        }
      }, 100);
    });
  }
});
