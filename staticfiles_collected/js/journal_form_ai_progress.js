// static/js/journal_form_ai_progress.js

document.addEventListener("DOMContentLoaded", function () {
  const journalForm = document.getElementById("journal-entry-form");
  const saveButton = document.getElementById("save-entry-button"); // Ensure your save button has this ID

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
  const totalAiTasks = 3; // Quote, Mood, Tags

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  const csrftoken = getCookie("csrftoken");

  function showProgressModal(isUpdate = false) {
    if (
      !progressModal ||
      !progressModalContent ||
      !progressBar ||
      !progressPercentageText ||
      !progressMessage ||
      !progressTitle ||
      !taskStatusList ||
      !successMessageDiv ||
      !spinner
    ) {
      console.error("One or more progress modal elements not found.");
      return;
    }
    progressTitle.textContent = isUpdate
      ? "Updating your masterpiece..."
      : "Crafting your insights...";
    progressMessage.textContent =
      "Please wait a moment while we enhance your journal entry.";
    progressBar.style.width = "5%"; // Start with a small amount of progress
    progressPercentageText.textContent = "5%";
    taskStatusList.innerHTML = `
            <li id="status-quote" class="text-gray-500 dark:text-gray-400">Quote Generation: <span class="font-semibold">Initializing...</span></li>
            <li id="status-mood" class="text-gray-500 dark:text-gray-400">Mood Detection: <span class="font-semibold">Initializing...</span></li>
            <li id="status-tags" class="text-gray-500 dark:text-gray-400">Tag Suggestion: <span class="font-semibold">Initializing...</span></li>
        `;
    successMessageDiv.classList.add("hidden");
    spinner.classList.remove("hidden");
    progressBar.classList.remove("bg-green-500", "bg-red-500"); // Reset bar color
    progressBar.classList.add("bg-primary-light", "dark:bg-primary-dark");

    progressModal.classList.remove("hidden");
    progressModal.classList.add("flex");
    // Force reflow for transition
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
      if (saveButton) {
        // Re-enable save button if modal is hidden due to error
        saveButton.disabled = false;
        saveButton.classList.remove("opacity-50", "cursor-not-allowed");
      }
    }, 300);
  }

  function updateTaskStatusUI(taskType, status) {
    const statusElement = document.getElementById(`status-${taskType}`);
    if (statusElement) {
      let statusText = "Pending...";
      let statusIcon = "<i class='fas fa-spinner fa-spin ml-1'></i>"; // Default pending icon
      let textColor = "text-yellow-500 dark:text-yellow-400";

      if (status === "SUCCESS") {
        statusText = "Done";
        statusIcon = "<i class='fas fa-check-circle text-green-500 ml-1'></i>";
        textColor = "text-green-600 dark:text-green-400";
      } else if (status === "FAILURE") {
        statusText = "Failed";
        statusIcon = "<i class='fas fa-times-circle text-red-500 ml-1'></i>";
        textColor = "text-red-600 dark:text-red-400";
      } else if (status === "STARTED" || status === "RETRY") {
        statusText = "Processing...";
      } else if (status === "PENDING" && taskType !== "initial") {
        // Don't show spinner if truly just pending
        statusIcon = "<i class='far fa-clock ml-1'></i>";
        textColor = "text-gray-500 dark:text-gray-400";
      }

      statusElement.innerHTML = `${
        taskType.charAt(0).toUpperCase() + taskType.slice(1)
      }: <span class="font-semibold ${textColor}">${statusText} ${statusIcon}</span>`;
    }
  }

  function updateOverallProgressUI(
    completedTasks,
    totalTasksToConsider,
    hasFailure
  ) {
    const percentage =
      totalTasksToConsider > 0
        ? Math.round((completedTasks / totalTasksToConsider) * 100)
        : 0;
    if (progressBar) {
      progressBar.style.width = `${percentage}%`;
      if (hasFailure && completedTasks < totalTasksToConsider) {
        progressBar.classList.remove(
          "bg-primary-light",
          "dark:bg-primary-dark",
          "bg-green-500"
        );
        progressBar.classList.add("bg-red-500");
      } else if (percentage === 100) {
        progressBar.classList.remove(
          "bg-primary-light",
          "dark:bg-primary-dark",
          "bg-red-500"
        );
        progressBar.classList.add("bg-green-500"); // Green on full success
      }
    }
    if (progressPercentageText)
      progressPercentageText.textContent = `${percentage}%`;
  }

  async function pollTaskStatus(entryId, initialTaskIds, redirectUrl) {
    if (!entryId) {
      console.error("Entry ID is missing for polling.");
      hideProgressModal();
      alert("Error: Could not track AI processing. Entry ID missing.");
      return;
    }

    const statusUrl = `/journal/entry/${entryId}/ai-status/`;
    let attempts = 0;
    const maxAttempts = 20; // Poll for a maximum of 20 * 3 = 60 seconds

    pollingInterval = setInterval(async () => {
      attempts++;
      if (attempts > maxAttempts) {
        clearInterval(pollingInterval);
        logger.warn("Max polling attempts reached for entry ID:", entryId);
        progressTitle.textContent = "Processing Update";
        progressMessage.innerHTML = `<span class="text-yellow-500 dark:text-yellow-300">AI tasks are taking longer than expected. Your entry is saved. You can check back on its detail page shortly.</span>`;
        spinner.classList.add("hidden");
        setTimeout(() => {
          window.location.href = redirectUrl; // Redirect anyway
        }, 4000);
        return;
      }

      try {
        const response = await fetch(statusUrl);
        if (!response.ok) {
          // If status endpoint itself fails (e.g. 404, 500 from status view)
          throw new Error(
            `AI status check failed: ${response.status} ${response.statusText}`
          );
        }
        const data = await response.json();
        console.log("Polling status response:", data);

        if (data.status !== "ok") {
          throw new Error(
            data.message || "Unknown error from AI status endpoint."
          );
        }

        let completedCount = 0;
        let hasFailure = false;
        const taskTypes = ["quote", "mood", "tags"];

        taskTypes.forEach((taskType) => {
          const status = data.task_statuses[`${taskType}_status`];
          updateTaskStatusUI(taskType, status);
          if (status === "SUCCESS") {
            completedCount++;
          } else if (status === "FAILURE") {
            completedCount++; // Count failures as "processed" for progress bar completion
            hasFailure = true;
          }
        });

        updateOverallProgressUI(completedCount, totalAiTasks, hasFailure);

        if (data.all_done) {
          clearInterval(pollingInterval);
          spinner.classList.add("hidden");
          if (hasFailure) {
            progressTitle.textContent = "Processing Partially Complete";
            progressMessage.innerHTML = `<span class="text-yellow-600 dark:text-yellow-400">Some AI enhancements encountered issues. Your entry is saved.</span>`;
          } else {
            progressTitle.textContent = "Enhancements Complete!";
            progressMessage.textContent =
              "Your journal entry has been beautifully crafted.";
            successMessageDiv.classList.remove("hidden");
          }
          setTimeout(
            () => {
              window.location.href = redirectUrl;
            },
            hasFailure ? 3000 : 1500
          );
        }
      } catch (error) {
        console.error("Polling error:", error);
        progressMessage.textContent = "Error checking AI status. Retrying...";
        // The interval will continue to retry up to maxAttempts
      }
    }, 3000); // Poll every 3 seconds
  }

  if (journalForm && saveButton) {
    journalForm.addEventListener("submit", async function (event) {
      event.preventDefault();

      // Call your existing tag update function if it's globally available
      if (typeof window.updatePillsAndHiddenInput === "function") {
        window.updatePillsAndHiddenInput();
        console.log("Called window.updatePillsAndHiddenInput()");
      } else {
        console.warn(
          "Global function updatePillsAndHiddenInput not found for tags."
        );
      }

      const isUpdate = journalForm.action.includes("/edit/");
      showProgressModal(isUpdate);
      saveButton.disabled = true;
      saveButton.classList.add("opacity-50", "cursor-not-allowed");

      const formData = new FormData(journalForm);
      const formActionUrl = journalForm.action;

      try {
        const response = await fetch(formActionUrl, {
          method: "POST",
          body: formData,
          headers: {
            "X-CSRFToken": csrftoken, // Ensure CSRF token is sent
            "X-Requested-With": "XMLHttpRequest",
          },
        });

        const responseData = await response.json(); // Try to parse JSON regardless of status for more info

        if (!response.ok) {
          console.error("Form submission error response:", responseData);
          let errorMessages =
            "Submission failed. Please check the form for errors.";
          if (responseData.form_errors || responseData.formset_errors) {
            errorMessages =
              "Please correct the errors highlighted in the form. The page will reload.";
            // Here, you could attempt to parse responseData.form_errors (which is JSON string)
            // and display them in the modal, but a reload is simpler for now.
          } else if (responseData.message) {
            errorMessages = responseData.message;
          }
          progressTitle.textContent = "Submission Error";
          progressMessage.innerHTML = `<span class="text-red-500">${errorMessages}</span>`;
          spinner.classList.add("hidden");
          setTimeout(() => {
            hideProgressModal();
            // Don't submit normally, let user fix errors if possible or show a persistent error
            // journalForm.submit();
            saveButton.disabled = false;
            saveButton.classList.remove("opacity-50", "cursor-not-allowed");
          }, 4000);
          return;
        }

        console.log("Form submission successful:", responseData);

        if (
          responseData.status === "success" &&
          responseData.entry_id &&
          responseData.redirect_url
        ) {
          progressMessage.textContent =
            "Entry saved! AI enhancements are now in progress...";
          pollTaskStatus(
            responseData.entry_id,
            responseData.task_ids,
            responseData.redirect_url
          );
        } else {
          // This case might happen if backend returns 200 OK but status is not 'success'
          throw new Error(
            responseData.message || "Unknown success response format."
          );
        }
      } catch (error) {
        console.error("AJAX submission processing error:", error);
        progressTitle.textContent = "Error";
        progressMessage.innerHTML = `<span class="text-red-500">An error occurred: ${error.message}. Please try again.</span>`;
        spinner.classList.add("hidden");
        setTimeout(hideProgressModal, 5000);
        // Re-enable button after error
        saveButton.disabled = false;
        saveButton.classList.remove("opacity-50", "cursor-not-allowed");
      }
      // Do not re-enable button here if polling has started. It's handled in hideProgressModal or success.
    });
  } else {
    console.warn(
      "Journal form or save button not found for AI progress script."
    );
  }
});
