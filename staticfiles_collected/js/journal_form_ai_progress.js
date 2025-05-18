// static/js/journal_form_ai_progress.js

document.addEventListener("DOMContentLoaded", function () {
  const journalForm = document.getElementById("journal-entry-form");
  const saveButton = document.getElementById("save-entry-button"); // Assuming your save button has this ID

  const progressModal = document.getElementById("ai-progress-modal");
  const progressModalContent = document.getElementById(
    "ai-progress-modal-content"
  );
  const progressBar = document.getElementById("ai-progress-bar");
  const progressPercentageText = document.getElementById(
    "ai-progress-percentage"
  );
  const progressMessage = document.getElementById("ai-progress-message");
  const progressTitle = document.getElementById("ai-progress-title");
  const taskStatusList = document.getElementById("ai-task-status-list");
  const successMessageDiv = document.getElementById("ai-success-message");
  const spinner = document.getElementById("ai-spinner");

  let pollingInterval;
  let totalTasks = 3; // Quote, Mood, Tags

  function showProgressModal(isUpdate = false) {
    if (!progressModal || !progressModalContent) return;
    progressTitle.textContent = isUpdate
      ? "Updating your masterpiece..."
      : "Crafting your insights...";
    progressMessage.textContent =
      "Please wait a moment while we enhance your journal entry.";
    progressBar.style.width = "0%";
    progressPercentageText.textContent = "0%";
    taskStatusList.innerHTML = `
            <li id="status-quote">Quote: <span class="font-semibold">Pending...</span></li>
            <li id="status-mood">Mood: <span class="font-semibold">Pending...</span></li>
            <li id="status-tags">Tags: <span class="font-semibold">Pending...</span></li>
        `;
    successMessageDiv.classList.add("hidden");
    spinner.classList.remove("hidden");

    progressModal.classList.remove("hidden");
    progressModal.classList.add("flex"); // Use flex to center
    // Trigger reflow for transition
    void progressModalContent.offsetWidth;
    progressModalContent.classList.remove("opacity-0", "scale-95");
    progressModalContent.classList.add("opacity-100", "scale-100");
  }

  function hideProgressModal() {
    if (!progressModal || !progressModalContent) return;
    progressModalContent.classList.add("opacity-0", "scale-95");
    progressModalContent.classList.remove("opacity-100", "scale-100");
    setTimeout(() => {
      progressModal.classList.add("hidden");
      progressModal.classList.remove("flex");
    }, 300); // Match transition duration
  }

  function updateTaskStatus(taskType, status) {
    const statusElement = document.getElementById(`status-${taskType}`);
    if (statusElement) {
      let statusText = "Pending...";
      let statusColor = "text-gray-500 dark:text-gray-400"; // Default
      if (status === "SUCCESS") {
        statusText = "Done <i class='fas fa-check-circle text-green-500'></i>";
        statusColor = "text-green-600 dark:text-green-400";
      } else if (status === "FAILURE") {
        statusText = "Failed <i class='fas fa-times-circle text-red-500'></i>";
        statusColor = "text-red-600 dark:text-red-400";
      } else if (status === "STARTED" || status === "RETRY") {
        statusText = "Processing...";
        statusColor = "text-yellow-500 dark:text-yellow-400";
      }
      statusElement.innerHTML = `${
        taskType.charAt(0).toUpperCase() + taskType.slice(1)
      }: <span class="font-semibold ${statusColor}">${statusText}</span>`;
    }
  }

  function updateOverallProgress(completedTasks) {
    const percentage = Math.round((completedTasks / totalTasks) * 100);
    if (progressBar) progressBar.style.width = `${percentage}%`;
    if (progressPercentageText)
      progressPercentageText.textContent = `${percentage}%`;

    if (completedTasks === totalTasks) {
      progressMessage.textContent = "Almost there...";
    }
  }

  function pollTaskStatus(entryId, taskIds, redirectUrl) {
    if (!entryId) {
      console.error("Entry ID is missing for polling.");
      hideProgressModal();
      // Potentially show an error to the user
      return;
    }

    const statusUrl = `/journal/entry/${entryId}/ai-status/`;
    let completedTasks = 0;

    pollingInterval = setInterval(async () => {
      try {
        const response = await fetch(statusUrl);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        console.log("Polling status:", data);

        completedTasks = 0;
        let quoteDone = false,
          moodDone = false,
          tagsDone = false;

        if (data.task_statuses) {
          if (
            data.task_statuses.quote_status === "SUCCESS" ||
            data.task_statuses.quote_status === "FAILURE"
          ) {
            completedTasks++;
            quoteDone = true;
          }
          updateTaskStatus("quote", data.task_statuses.quote_status);

          if (
            data.task_statuses.mood_status === "SUCCESS" ||
            data.task_statuses.mood_status === "FAILURE"
          ) {
            completedTasks++;
            moodDone = true;
          }
          updateTaskStatus("mood", data.task_statuses.mood_status);

          if (
            data.task_statuses.tags_status === "SUCCESS" ||
            data.task_statuses.tags_status === "FAILURE"
          ) {
            completedTasks++;
            tagsDone = true;
          }
          updateTaskStatus("tags", data.task_statuses.tags_status);
        }

        updateOverallProgress(completedTasks);

        if (data.all_done || (quoteDone && moodDone && tagsDone)) {
          clearInterval(pollingInterval);
          spinner.classList.add("hidden");
          progressTitle.textContent = "Enhancements Complete!";
          progressMessage.textContent =
            "Your journal entry has been beautifully crafted.";
          successMessageDiv.classList.remove("hidden");
          // Redirect after a short delay
          setTimeout(() => {
            window.location.href = redirectUrl;
          }, 1500); // 1.5 seconds delay
        }
      } catch (error) {
        console.error("Polling error:", error);
        progressMessage.textContent =
          "Error checking AI status. Will keep trying...";
        // Optionally, stop polling after too many errors
      }
    }, 3000); // Poll every 3 seconds
  }

  if (journalForm && saveButton) {
    journalForm.addEventListener("submit", async function (event) {
      event.preventDefault(); // Stop default form submission

      // Ensure hidden tags input is up-to-date (if your tag script doesn't do this on submit)
      if (window.updatePillsAndHiddenInput) {
        // Check if the function from tag script exists
        window.updatePillsAndHiddenInput();
      }

      const isUpdate = !!journalForm.action.match(/\/\d+\/edit\/$/); // Simple check if it's an update form
      showProgressModal(isUpdate);
      saveButton.disabled = true; // Disable button to prevent multiple submissions
      saveButton.classList.add("opacity-50", "cursor-not-allowed");

      const formData = new FormData(journalForm);
      const formActionUrl = journalForm.action;

      try {
        const response = await fetch(formActionUrl, {
          method: "POST",
          body: formData,
          headers: {
            // 'X-CSRFToken': formData.get('csrfmiddlewaretoken'), // FormData includes it
            "X-Requested-With": "XMLHttpRequest", // To let Django know it's an AJAX request
          },
        });

        if (!response.ok) {
          // Handle non-2xx responses (e.g., validation errors)
          const errorData = await response.json();
          console.error("Form submission error:", errorData);
          let errorMessages =
            "Submission failed. Please check the form for errors.";
          if (errorData.form_errors || errorData.formset_errors) {
            // You might want to parse these and display them more nicely
            errorMessages =
              "Please correct the errors highlighted in the form.";
            // The form should re-render with errors from Django if form_invalid is hit
            // For now, just a generic message and hide progress.
            // Or, you could try to parse and display them in the modal.
          }
          progressTitle.textContent = "Submission Error";
          progressMessage.innerHTML = `<span class="text-red-500">${errorMessages}</span> <br>The page will reload to show details.`;
          spinner.classList.add("hidden");
          setTimeout(() => {
            hideProgressModal();
            journalForm.submit(); // Fallback to normal submission to show Django's error rendering
          }, 3000);
          return;
        }

        const data = await response.json();
        console.log("Form submission successful:", data);

        if (data.status === "success" && data.entry_id && data.redirect_url) {
          progressMessage.textContent =
            "Entry saved! Starting AI enhancements...";
          pollTaskStatus(data.entry_id, data.task_ids, data.redirect_url);
        } else {
          throw new Error(
            data.message || "Unknown error after form submission."
          );
        }
      } catch (error) {
        console.error("AJAX submission error:", error);
        progressTitle.textContent = "Error";
        progressMessage.innerHTML = `<span class="text-red-500">An error occurred: ${error.message}. Please try again.</span>`;
        spinner.classList.add("hidden");
        // Optionally hide modal after a delay or allow user to close
        setTimeout(hideProgressModal, 5000);
      } finally {
        // Re-enable button only if there was a non-redirecting error
        // If polling starts, button remains disabled until redirect.
        if (!pollingInterval) {
          // If polling didn't start due to an error
          saveButton.disabled = false;
          saveButton.classList.remove("opacity-50", "cursor-not-allowed");
        }
      }
    });
  } else {
    console.warn(
      "Journal form or save button not found for AI progress script."
    );
  }
});
