document.addEventListener("DOMContentLoaded", () => {
  const room = document.querySelector("[data-chat-room]");
  if (!room) {
    return;
  }

  const groupId = room.dataset.groupId;
  const maxLength = Number(room.dataset.maxLength || "2000");
  const messageList = room.querySelector("[data-message-list]");
  const rosterList = room.querySelector("[data-roster-list]");
  const form = room.querySelector("[data-chat-form]");
  const textarea = form.querySelector("textarea");
  const sendButton = form.querySelector("button[type='submit']");
  const submitLabel = form.querySelector("[data-submit-label]");
  const charCount = form.querySelector("[data-char-count]");
  const errorBox = room.querySelector("[data-chat-error]");
  const socketIndicator = room.querySelector("[data-socket-state]");
  const yourAlias = room.querySelector(".roster-self")?.textContent || "";

  let socket = null;
  let reconnectTimer = null;
  let closedByPage = false;
  let socketState = "connecting";

  const connect = () => {
    if (closedByPage) {
      return;
    }

    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    updateSocketState("connecting", "Connecting...");
    socket = new WebSocket(`${protocol}://${window.location.host}/ws/groups/${groupId}`);

    socket.addEventListener("open", () => {
      updateSocketState("live", "Live");
      hideError();
    });

    socket.addEventListener("message", (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === "message") {
        appendMessage(payload.message);
        return;
      }
      if (payload.type === "roster") {
        renderRoster(payload.aliases || []);
        return;
      }
      if (payload.type === "error") {
        showError(payload.message);
      }
    });

    socket.addEventListener("close", () => {
      if (closedByPage) {
        return;
      }
      updateSocketState("offline", "Reconnecting...");
      scheduleReconnect();
    });

    socket.addEventListener("error", () => {
      updateSocketState("error", "Connection issue");
      showError("Connection hiccup. Trying to reconnect.");
    });
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const body = textarea.value.trim();

    if (!body) {
      syncSendAvailability();
      return;
    }

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      showError("Still reconnecting. Try again in a moment.");
      return;
    }

    if (body.length > maxLength) {
      showError(`Messages must be ${maxLength} characters or fewer.`);
      return;
    }

    socket.send(JSON.stringify({ body }));
    clearComposer();
    hideError();
    textarea.focus();
  });

  textarea.addEventListener("input", () => {
    autoResize();
    updateCharacterCount();
    if (textarea.value.length <= maxLength && errorBox.textContent.includes("characters")) {
      hideError();
    }
  });

  textarea.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.ctrlKey && !event.metaKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  window.addEventListener("online", () => {
    if (!socket || socket.readyState === WebSocket.CLOSED) {
      connect();
    }
  });

  function appendMessage(message, forceScroll = false) {
    const pinnedToBottom = forceScroll || isNearBottom();
    room.querySelector("[data-empty-chat]")?.remove();

    const card = document.createElement("article");
    card.className = "message-card";
    if (message.alias === yourAlias) {
      card.classList.add("message-self");
    }

    const meta = document.createElement("div");
    meta.className = "message-meta";

    const name = document.createElement("strong");
    name.textContent = message.alias;

    const time = document.createElement("span");
    time.textContent = message.created_at;

    const body = document.createElement("p");
    body.textContent = message.body;

    meta.append(name, time);
    card.append(meta, body);
    messageList.appendChild(card);

    if (pinnedToBottom) {
      scrollToBottom();
    }
  }

  function renderRoster(aliases) {
    rosterList.innerHTML = "";
    const sortedAliases = [...aliases].sort((left, right) => left.localeCompare(right));

    for (const alias of sortedAliases) {
      const item = document.createElement("li");
      item.className = "roster-item";
      if (alias === yourAlias) {
        item.classList.add("roster-self");
      }
      item.textContent = alias;
      rosterList.appendChild(item);
    }
  }

  function updateSocketState(state, indicatorLabel) {
    socketState = state;
    socketIndicator.dataset.state = state;
    socketIndicator.textContent = indicatorLabel;
    syncSendAvailability();
  }

  function updateCharacterCount() {
    const length = textarea.value.length;
    if (charCount) {
      charCount.textContent = `${length} / ${maxLength}`;
      charCount.dataset.overLimit = String(length > maxLength);
    }
    syncSendAvailability();
  }

  function syncSendAvailability() {
    const hasText = textarea.value.trim().length > 0;
    const validLength = textarea.value.length <= maxLength;
    sendButton.disabled = socketState !== "live" || !hasText || !validLength;

    if (!submitLabel) {
      return;
    }

    if (socketState === "live") {
      submitLabel.textContent = "Send anonymously";
      return;
    }

    submitLabel.textContent = "Connecting...";
  }

  function autoResize() {
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 220)}px`;
  }

  function clearComposer() {
    textarea.value = "";
    autoResize();
    updateCharacterCount();
  }

  function isNearBottom() {
    return messageList.scrollHeight - messageList.scrollTop - messageList.clientHeight < 120;
  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
  }

  function hideError() {
    errorBox.classList.add("hidden");
    errorBox.textContent = "";
  }

  function scheduleReconnect() {
    if (reconnectTimer || closedByPage) {
      return;
    }

    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, 1800);
  }

  function scrollToBottom() {
    messageList.scrollTop = messageList.scrollHeight;
  }

  autoResize();
  updateCharacterCount();
  connect();
  scrollToBottom();

  window.addEventListener("beforeunload", () => {
    closedByPage = true;
    window.clearTimeout(reconnectTimer);
    if (socket && socket.readyState <= WebSocket.OPEN) {
      socket.close();
    }
  });
});