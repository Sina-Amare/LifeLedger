/**
 * Handles the AI processing progress modal for the journal entry form.
 * This script intercepts the form submission, shows a progress modal,
 * and polls the backend for the status of asynchronous AI tasks.
 */
document.addEventListener("DOMContentLoaded", function () {
  const journalForm = document.getElementById("journal-entry-form");
  const saveButton = document.getElementById("save-entry-button");

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
  const totalAiTasks = 3; // Corresponds to quote, mood, and tags.

  if (!journalForm || !saveButton) {
    console.warn(
      "Journal form or save button not found. Progress script is inactive."
    );
    return;
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

  function showProgressModal(isUpdate) {
    progressTitle.textContent = isUpdate
      ? "Updating your masterpiece..."
      : "Crafting your insights...";
    progressMessage.textContent =
      "Please wait a moment while we enhance your journal entry.";
    progressBar.style.width = "5%";
    progressPercentageText.textContent = "5%";
    taskStatusList.innerHTML = `
          <li id="status-quote" class="text-gray-500 dark:text-gray-400">Quote Generation: <span class="font-semibold">Initializing...</span></li>
          <li id="status-mood" class="text-gray-500 dark:text-gray-400">Mood Detection: <span class="font-semibold">Initializing...</span></li>
          <li id="status-tags" class="text-gray-500 dark:text-gray-400">Tag Suggestion: <span class="font-semibold">Initializing...</span></li>
      `;
    successMessageDiv.classList.add("hidden");
    spinner.classList.remove("hidden");
    progressBar.classList.remove("bg-green-500", "bg-red-500");
    progressBar.classList.add("bg-primary-light", "dark:bg-primary-dark");

    progressModal.classList.remove("hidden");
    progressModal.classList.add("flex");
    void progressModalContent.offsetWidth; // Reflow
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
        saveButton.disabled = false;
        saveButton.classList.remove("opacity-50", "cursor-not-allowed");
      }
    }, 300);
  }

  function updateTaskStatusUI(taskType, status) {
    const statusElement = document.getElementById(`status-${taskType}`);
    if (statusElement) {
      let statusText = "Pending...";
      let statusIcon = "<i class='far fa-clock ml-1'></i>";
      let textColor = "text-gray-500 dark:text-gray-400";

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
        statusIcon = "<i class='fas fa-spinner fa-spin ml-1'></i>";
        textColor = "text-yellow-500 dark:text-yellow-400";
      } else if (status === "DISABLED_BY_USER") {
        statusText = "Disabled";
        statusIcon = "<i class='fas fa-ban text-gray-400 ml-1'></i>";
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
        progressBar.className =
          "h-full rounded-full bg-red-500 transition-all duration-500";
      } else if (percentage === 100) {
        progressBar.className =
          "h-full rounded-full bg-green-500 transition-all duration-500";
      }
    }
    if (progressPercentageText)
      progressPercentageText.textContent = `${percentage}%`;
  }

  async function pollTaskStatus(entryId, redirectUrl) {
    const statusUrl = `/journal/entry/${entryId}/ai-status/`;
    let attempts = 0;
    const maxAttempts = 20;

    pollingInterval = setInterval(async () => {
      attempts++;
      if (attempts > maxAttempts) {
        clearInterval(pollingInterval);
        window.location.href = redirectUrl;
        return;
      }

      try {
        const response = await fetch(statusUrl);
        const data = await response.json();

        if (data.status !== "ok")
          throw new Error(data.message || "Status check failed.");

        let completedCount = 0;
        let hasFailure = false;
        const taskTypes = ["quote", "mood", "tags"];

        taskTypes.forEach((taskType) => {
          const status = data.task_statuses[`${taskType}_status`];
          updateTaskStatusUI(taskType, status);
          if (
            status === "SUCCESS" ||
            status === "FAILURE" ||
            status === "DISABLED_BY_USER"
          ) {
            completedCount++;
            if (status === "FAILURE") hasFailure = true;
          }
        });

        updateOverallProgressUI(completedCount, totalAiTasks, hasFailure);

        if (data.all_done) {
          clearInterval(pollingInterval);
          spinner.classList.add("hidden");
          progressTitle.textContent = hasFailure
            ? "Processing Partially Complete"
            : "Enhancements Complete!";
          successMessageDiv.classList.remove("hidden");
          setTimeout(
            () => (window.location.href = redirectUrl),
            hasFailure ? 3000 : 1500
          );
        }
      } catch (error) {
        console.error("Polling error:", error);
      }
    }, 3000);
  }

  if (journalForm) {
    journalForm.addEventListener("submit", async function (event) {
      event.preventDefault();

      if (typeof window.updatePillsAndHiddenInput === "function") {
        window.updatePillsAndHiddenInput();
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
            "X-CSRFToken": csrftoken,
            "X-Requested-With": "XMLHttpRequest",
          },
        });

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
          const responseData = await response.json();

          if (!response.ok) {
            console.error("Form submission error response:", responseData);
            progressTitle.textContent = "Submission Error";
            progressMessage.innerHTML = `<span class="text-red-500">Please check the form for errors. The page will now reload.</span>`;
            spinner.classList.add("hidden");
            setTimeout(() => window.location.reload(), 4000);
            return;
          }

          if (
            responseData.status === "success" &&
            responseData.entry_id &&
            responseData.redirect_url
          ) {
            progressMessage.textContent =
              "Entry saved! AI enhancements are in progress...";
            pollTaskStatus(responseData.entry_id, responseData.redirect_url);
          } else {
            throw new Error(
              responseData.message ||
                "Received an unexpected success response format."
            );
          }
        } else {
          const errorText = await response.text();
          console.error("Server returned non-JSON response:", errorText);
          throw new Error(
            "The server responded with an unexpected error. Please check the server logs."
          );
        }
      } catch (error) {
        console.error("AJAX submission processing error:", error);
        progressTitle.textContent = "Error";
        progressMessage.innerHTML = `<span class="text-red-500">${error.message}</span>`;
        spinner.classList.add("hidden");
        setTimeout(hideProgressModal, 6000);
      }
    });
  }
});
