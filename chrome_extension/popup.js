// Zenrex Assistant — Popup logic
const statusEl = document.getElementById("status");
const pairForm = document.getElementById("pair-form");
const connectedActions = document.getElementById("connected-actions");
const codeInput = document.getElementById("code-input");
const pairBtn = document.getElementById("pair-btn");
const unpairBtn = document.getElementById("unpair-btn");

function setStatus(state, text) {
  statusEl.className = `status ${state}`;
  statusEl.textContent = text;
}

async function refreshStatus() {
  const resp = await chrome.runtime.sendMessage({ type: "get_status" });
  if (resp.connected) {
    setStatus("connected", "✅ متصل — الذكاء يقدر يتحكم بمتصفحك");
    pairForm.style.display = "none";
    connectedActions.style.display = "block";
  } else if (resp.paired) {
    setStatus("idle", "⏳ الإضافة مربوطة — تحاول الاتصال...");
    pairForm.style.display = "block";
    connectedActions.style.display = "block";
  } else {
    setStatus("disconnected", "❌ غير مربوط بمشروع بعد");
    pairForm.style.display = "block";
    connectedActions.style.display = "none";
  }
}

pairBtn.addEventListener("click", async () => {
  const code = codeInput.value.trim().toUpperCase();
  if (code.length !== 6) {
    setStatus("disconnected", "الرمز يجب أن يكون 6 حروف");
    return;
  }
  await chrome.runtime.sendMessage({ type: "set_pairing_code", code });
  setTimeout(refreshStatus, 1500);
});

unpairBtn.addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "unpair" });
  refreshStatus();
});

codeInput.addEventListener("input", (e) => {
  e.target.value = e.target.value.toUpperCase().replace(/[^A-Z2-9]/g, "");
});
codeInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") pairBtn.click();
});

refreshStatus();
setInterval(refreshStatus, 3000);
