async function update(action = "status") {
  const result = await chrome.runtime.sendMessage({action});
  document.getElementById("status").textContent = result.status;
}
document.getElementById("connect").addEventListener("click", () => update("connect"));
void update();
setInterval(update, 1000);
