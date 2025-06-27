document.addEventListener("DOMContentLoaded", () => {
  // --- Thought Bubble Logic ---
  let activeBubble = null;
  let activeButton = null;

  document.querySelectorAll(".read-more").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation(); // Prevents click from bubbling up to the document

      const fullContentElement =
        button.parentElement.querySelector(".full-content");
      if (!fullContentElement) return;

      const fullContent =
        fullContentElement.textContent || "No content available";

      // If clicking the same button that's already active, close the bubble
      if (activeButton === button) {
        if (activeBubble) activeBubble.remove();
        activeBubble = null;
        activeButton.classList.remove("active");
        activeButton = null;
        return;
      }

      // If another bubble is open, close it first
      if (activeBubble) {
        activeBubble.remove();
        if (activeButton) activeButton.classList.remove("active");
      }

      activeButton = button;
      activeButton.classList.add("active");

      // Create and append the new bubble
      activeBubble = document.createElement("div");
      activeBubble.classList.add("thought-bubble");
      const closeBtn = document.createElement("button");
      closeBtn.classList.add("thought-bubble-close-btn");
      closeBtn.innerHTML = "&times;";
      activeBubble.appendChild(closeBtn);

      const contentNode = document.createElement("p");
      contentNode.textContent = fullContent;
      activeBubble.appendChild(contentNode);

      document.body.appendChild(activeBubble);

      // --- Position the bubble (simplified for robustness) ---
      const card = button.closest(".entry-card");
      const cardRect = card.getBoundingClientRect();
      const journalGroup = button.closest(".journal-group");
      const side = journalGroup.getAttribute("data-side");

      activeBubble.style.display = "block";
      const bubbleRect = activeBubble.getBoundingClientRect();

      let left, top;
      const margin = 20;

      if (window.innerWidth <= 768 || side === "right") {
        left = cardRect.left - bubbleRect.width - margin;
        activeBubble.classList.add("right");
      } else {
        left = cardRect.right + margin;
        activeBubble.classList.remove("right");
      }

      top = cardRect.top + cardRect.height / 2 - bubbleRect.height / 2;

      // Viewport collision checks
      if (left < 10) left = 10;
      if (left + bubbleRect.width > window.innerWidth - 10)
        left = window.innerWidth - bubbleRect.width - 10;
      if (top < 10) top = 10;
      if (top + bubbleRect.height > window.innerHeight - 10)
        top = window.innerHeight - bubbleRect.height - 10;

      activeBubble.style.left = `${left + window.scrollX}px`;
      activeBubble.style.top = `${top + window.scrollY}px`;

      const buttonRect = button.getBoundingClientRect();
      const tailTop = buttonRect.top - top + buttonRect.height / 2;
      activeBubble.style.setProperty(
        "--tail-top",
        `${Math.max(10, Math.min(tailTop, bubbleRect.height - 25))}px`
      );

      closeBtn.addEventListener("click", () => {
        if (activeBubble) activeBubble.remove();
        if (activeButton) activeButton.classList.remove("active");
        activeBubble = null;
        activeButton = null;
      });
    });
  });

  // Close bubble when clicking outside of it
  document.addEventListener("click", (e) => {
    if (
      activeBubble &&
      !activeBubble.contains(e.target) &&
      !e.target.closest(".read-more")
    ) {
      activeBubble.remove();
      activeBubble = null;
      if (activeButton) {
        activeButton.classList.remove("active");
        activeButton = null;
      }
    }
  });

  // --- REBUILT Photo Gallery Logic ---
  document
    .querySelectorAll(".animated-photo-container")
    .forEach((galleryContainer) => {
      const prevButton = galleryContainer.querySelector(".gallery-nav.prev");
      const nextButton = galleryContainer.querySelector(".gallery-nav.next");
      const items = galleryContainer.querySelectorAll(".gallery-item");

      // Exit if there are no images at all
      if (items.length === 0) {
        return;
      }

      let currentIndex = 0;

      const showImage = (index) => {
        items.forEach((item, i) => {
          // Use classList.toggle for cleaner add/remove logic
          item.classList.toggle("active", i === index);
        });
      };

      // Ensure the first image is always displayed on load
      showImage(currentIndex);

      // Only attach event listeners if there's more than one image and the buttons exist
      if (items.length > 1 && prevButton && nextButton) {
        prevButton.addEventListener("click", () => {
          currentIndex = (currentIndex - 1 + items.length) % items.length;
          showImage(currentIndex);
        });

        nextButton.addEventListener("click", () => {
          currentIndex = (currentIndex + 1) % items.length;
          showImage(currentIndex);
        });
      }
    });
});
