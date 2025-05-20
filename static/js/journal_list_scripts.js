document.addEventListener("DOMContentLoaded", () => {
  let activeBubble = null;
  let activeButton = null;

  const readMoreButtons = document.querySelectorAll(".read-more");
  console.log("Number of Read More buttons found:", readMoreButtons.length);
  readMoreButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      console.log(
        "Read More button clicked for entry:",
        button.getAttribute("data-debug")
      );

      const fullContentElement =
        button.parentElement.querySelector(".full-content");
      if (!fullContentElement) {
        console.error(
          "Full content element not found for entry:",
          button.getAttribute("data-debug")
        );
        return;
      }
      const fullContent =
        fullContentElement.textContent || "No content available";
      if (!fullContent.trim()) {
        console.warn(
          "Full content is empty for entry:",
          button.getAttribute("data-debug")
        );
      }

      // Close any existing bubble
      if (activeBubble && activeButton !== button) {
        activeBubble.remove();
        activeBubble = null;
        activeButton.classList.remove("active");
      }

      // Toggle the bubble for the clicked button
      if (activeButton === button && activeBubble) {
        activeBubble.remove();
        activeBubble = null;
        activeButton.classList.remove("active");
        activeButton = null;
        return;
      }

      activeButton = button;
      activeButton.classList.add("active");

      // Create thought bubble
      activeBubble = document.createElement("div");
      activeBubble.classList.add("thought-bubble");
      const closeBtn = document.createElement("button");
      closeBtn.classList.add("thought-bubble-close-btn");
      closeBtn.textContent = "×";
      closeBtn.addEventListener("click", () => {
        activeBubble.remove();
        activeButton.classList.remove("active");
        activeBubble = null;
        activeButton = null;
      });
      activeBubble.appendChild(closeBtn);
      activeBubble.appendChild(document.createTextNode(fullContent));
      document.body.appendChild(activeBubble);

      // Force reflow to get accurate dimensions
      activeBubble.style.display = "block";
      activeBubble.style.visibility = "hidden";
      void activeBubble.offsetWidth; // Trigger reflow
      const bubbleWidth = activeBubble.offsetWidth;
      const bubbleHeight = activeBubble.offsetHeight;
      activeBubble.style.visibility = "visible";

      // Determine the position based on journal side
      const journalGroup = button.closest(".journal-group");
      const side = journalGroup.getAttribute("data-side");
      const card = button.closest(".entry-card");
      const cardRect = card.getBoundingClientRect();
      const timelineContainer = document.querySelector(".timeline-container");
      const timelineRect = timelineContainer.getBoundingClientRect();
      const timelineCenter = timelineRect.left + timelineRect.width / 2;
      const scrollX = window.scrollX || window.pageXOffset;
      const scrollY = window.scrollY || window.pageYOffset;
      const margin = 20;

      // Calculate initial position once, relative to the document
      let bubbleLeft, bubbleTop;
      if (side === "left") {
        // Left-side entry, place bubble on the right side
        activeBubble.classList.remove("right"); // Tail points left
        bubbleLeft = timelineCenter + margin + scrollX;
      } else {
        // Right-side entry, place bubble on the left side
        activeBubble.classList.add("right"); // Tail points right
        bubbleLeft = timelineCenter - bubbleWidth - margin + scrollX;
      }
      // Align vertically with the card's center, relative to document
      bubbleTop =
        cardRect.top + cardRect.height / 2 - bubbleHeight / 2 + scrollY;

      // Adjust tail position to align with the "Read More" button
      const buttonRect = button.getBoundingClientRect();
      const tailTop =
        buttonRect.top + buttonRect.height / 2 - (bubbleTop - scrollY);
      const minTailTop = 10;
      const maxTailTop = bubbleHeight - 25;
      const clampedTailTop = Math.min(
        Math.max(tailTop, minTailTop),
        maxTailTop
      );
      activeBubble.style.setProperty("--tail-top", `${clampedTailTop}px`);

      // Adjust to stay within viewport at the time of display
      if (bubbleLeft + bubbleWidth > window.innerWidth) {
        bubbleLeft = window.innerWidth - bubbleWidth - 10;
      } else if (bubbleLeft < 0) {
        bubbleLeft = 10;
      }
      if (bubbleTop + bubbleHeight > document.documentElement.scrollHeight) {
        bubbleTop = document.documentElement.scrollHeight - bubbleHeight - 10;
      } else if (bubbleTop < 0) {
        bubbleTop = 10;
      }

      console.log("Bubble dimensions:", bubbleWidth, bubbleHeight);
      console.log("Bubble position:", bubbleLeft, bubbleTop);
      console.log(
        "Timeline center:",
        timelineCenter,
        "Scroll:",
        scrollX,
        scrollY
      );
      console.log("Journal side:", side);

      activeBubble.style.left = `${bubbleLeft}px`;
      activeBubble.style.top = `${bubbleTop}px`;
      activeBubble.style.display = "block";
    });
  });

  // Close bubble when clicking outside
  document.addEventListener("click", (e) => {
    if (
      activeBubble &&
      !e.target.classList.contains("read-more") &&
      !activeBubble.contains(e.target)
    ) {
      activeBubble.remove();
      activeBubble = null;
      if (activeButton) {
        activeButton.classList.remove("active");
        activeButton = null;
      }
    }
  });
});
