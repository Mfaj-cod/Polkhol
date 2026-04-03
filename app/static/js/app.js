document.addEventListener("DOMContentLoaded", () => {
  const pickers = document.querySelectorAll("[data-user-picker]");
  for (const picker of pickers) {
    setupUserPicker(picker);
  }
});

function setupUserPicker(picker) {
  const input = picker.querySelector(".search-input");
  const resultsBox = picker.querySelector(".search-results");
  const selectedBox = picker.querySelector(".selected-users");
  const searchUrl = picker.dataset.searchUrl;
  const groupId = picker.dataset.groupId;
  const selected = new Map();
  let timer = null;
  let requestController = null;
  let lastQuery = "";

  renderSelectedState();

  input.addEventListener("focus", () => {
    const query = input.value.trim();
    if (!query.length) {
      setResultsMessage(selected.size ? "Type at least 2 characters to add more people." : "Type at least 2 characters to search.");
      return;
    }

    if (query.length < 2) {
      setResultsMessage("Type at least 2 characters to search.");
    }
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      clearTimeout(timer);
      input.value = "";
      lastQuery = "";
      if (requestController) {
        requestController.abort();
        requestController = null;
      }
      resultsBox.innerHTML = "";
      input.blur();
    }
  });

  input.addEventListener("input", () => {
    clearTimeout(timer);
    const query = input.value.trim();
    lastQuery = query;

    if (requestController) {
      requestController.abort();
      requestController = null;
    }

    if (!query.length) {
      resultsBox.innerHTML = "";
      return;
    }

    if (query.length < 2) {
      setResultsMessage("Type at least 2 characters to search.");
      return;
    }

    setResultsMessage("Searching...");
    timer = window.setTimeout(() => searchUsers(query), 220);
  });

  async function searchUsers(query) {
    requestController = new AbortController();

    try {
      const params = new URLSearchParams({ q: query });
      if (groupId) {
        params.set("group_id", groupId);
      }

      const response = await fetch(`${searchUrl}?${params.toString()}`, {
        headers: { Accept: "application/json" },
        signal: requestController.signal
      });

      if (!response.ok) {
        throw new Error("search-failed");
      }

      const payload = await response.json();
      if (query !== lastQuery) {
        return;
      }

      renderResults(payload.results || []);
    } catch (error) {
      if (error.name === "AbortError") {
        return;
      }
      setResultsMessage("Search unavailable right now.");
    } finally {
      requestController = null;
    }
  }

  function renderResults(results) {
    resultsBox.innerHTML = "";
    const availableResults = results.filter((result) => !selected.has(result.account_code));

    if (!results.length) {
      setResultsMessage("No matching users yet.");
      return;
    }

    if (!availableResults.length) {
      setResultsMessage("Everyone matching this search is already selected.");
      return;
    }

    for (const result of availableResults) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "result-item";

      const name = document.createElement("strong");
      name.textContent = result.username;

      const code = document.createElement("span");
      code.textContent = result.account_code;

      button.append(name, code);
      button.addEventListener("click", () => {
        addSelected(result);
        input.value = "";
        lastQuery = "";
        resultsBox.innerHTML = "";
        input.focus();
      });
      resultsBox.appendChild(button);
    }
  }

  function addSelected(result) {
    selected.set(result.account_code, result);

    const pill = document.createElement("div");
    pill.className = "selected-pill";
    pill.dataset.code = result.account_code;

    const label = document.createElement("span");
    label.textContent = `${result.username} - ${result.account_code}`;

    const hidden = document.createElement("input");
    hidden.type = "hidden";
    hidden.name = "member_codes";
    hidden.value = result.account_code;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "remove-pill";
    remove.textContent = "×";
    remove.setAttribute("aria-label", `Remove ${result.username}`);
    remove.addEventListener("click", () => {
      selected.delete(result.account_code);
      pill.remove();
      renderSelectedState();

      if (lastQuery.length >= 2) {
        searchUsers(lastQuery);
      } else if (!selected.size) {
        resultsBox.innerHTML = "";
      }
    });

    pill.append(label, remove, hidden);
    selectedBox.appendChild(pill);
    renderSelectedState();
  }

  function renderSelectedState() {
    const emptyState = selectedBox.querySelector(".selected-empty");
    if (selected.size) {
      emptyState?.remove();
      picker.dataset.hasSelection = "true";
      return;
    }

    picker.dataset.hasSelection = "false";
    selectedBox.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "result-empty selected-empty";
    empty.textContent = groupId ? "Nobody queued yet. Search and add new members." : "Nobody selected yet. Search to add people before you create the room.";
    selectedBox.appendChild(empty);
  }

  function setResultsMessage(message) {
    resultsBox.innerHTML = "";
    const state = document.createElement("div");
    state.className = "result-empty";
    state.textContent = message;
    resultsBox.appendChild(state);
  }
}