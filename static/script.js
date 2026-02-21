const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const typingIndicator = document.getElementById("typing-indicator");
const status = document.getElementById("status");

const clientIdKey = "gf_client_id";
let clientId = localStorage.getItem(clientIdKey);
if (!clientId) {
  clientId = `user_${crypto.randomUUID()}`;
  localStorage.setItem(clientIdKey, clientId);
}

const starter = "Hey... I missed you thoda sa. How was your day? 💜";
addMessage(starter, "ai");

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;

  addMessage(text, "user");
  messageInput.value = "";
  messageInput.focus();

  showTyping(true);

  try {
    status.textContent = "typing...";
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, client_id: clientId }),
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Something went wrong");

    const delay = Math.min(1800, 350 + data.reply.length * 12);
    await new Promise((resolve) => setTimeout(resolve, delay));

    addMessage(data.reply, "ai");
  } catch (error) {
    addMessage("Hmm... network ne mood kharab kar diya 😅 try again?", "ai");
    console.error(error);
  } finally {
    showTyping(false);
    status.textContent = "online";
  }
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

function showTyping(show) {
  typingIndicator.classList.toggle("hidden", !show);
  if (show) scrollToBottom();
}

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  chatWindow.appendChild(div);
  scrollToBottom();
}

function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}
