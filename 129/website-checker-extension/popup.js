const checkBtn = document.getElementById("checkBtn");
const resultDiv = document.getElementById("result");
const loader = document.getElementById("loader");

checkBtn.addEventListener("click", () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const url = tabs[0].url;

    resultDiv.classList.add("hidden");
    loader.classList.remove("hidden");

    fetch("http://localhost:5000/api/check", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ url })
    })
    .then(res => res.json())
    .then(data => {
      loader.classList.add("hidden");

      let verdictClass = "safe";
      if (data.final_verdict.includes("Unsafe")) verdictClass = "unsafe";
      else if (data.final_verdict.includes("moderately")) verdictClass = "moderate";

      resultDiv.innerHTML = `
        <div class="section" style="text-align:center">
          <b>FINAL VERDICT</b><br><br>
          <span class="badge ${verdictClass}">
            ${data.final_verdict}
          </span>
        </div>
      `;

      resultDiv.classList.remove("hidden");
    })
    .catch(() => {
      loader.classList.add("hidden");
      resultDiv.innerHTML = "❌ Backend not running";
      resultDiv.classList.remove("hidden");
    });
  });
});
