chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Trigger when page starts loading
  if (changeInfo.status === "loading" && tab.url) {

    fetch("http://localhost:5000/api/check", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ url: tab.url })
    })
    .then(res => res.json())
    .then(data => {

      let verdictClass = "safe";

      if (data.final_verdict.includes("Unsafe")) {
        verdictClass = "unsafe";
      } else if (data.final_verdict.includes("moderately")) {
        verdictClass = "moderate";
      }

      // 🚨 If UNSAFE → STOP and ALERT
      if (verdictClass === "unsafe") {
        chrome.scripting.executeScript({
          target: { tabId: tabId },
          func: () => {
            const proceed = confirm(
              "⚠️ WARNING: This website is UNSAFE!\n\nIt may be a phishing or harmful site.\n\nDo you still want to continue?"
            );

            if (!proceed) {
              window.location.href = "about:blank";
            }
          }
        });
      }

      // ⚠️ Moderate warning
      if (verdictClass === "moderate") {
        chrome.scripting.executeScript({
          target: { tabId: tabId },
          func: () => {
            const proceed = confirm(
              "⚠️ This site is moderately safe.\n\nProceed with caution.\n\nContinue?"
            );

            if (!proceed) {
              window.location.href = "about:blank";
            }
          }
        });
      }

    })
    .catch(err => console.log("Error:", err));
  }
});