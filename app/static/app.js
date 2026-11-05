// 避免重複送出：連點只送一次。沒有 JavaScript 時表單照常運作。
document.querySelectorAll("form[data-submit-once]").forEach((form) => {
  const button = form.querySelector("button[type=submit]");
  const label = button.textContent;
  let submitted = false;
  form.addEventListener("submit", (event) => {
    if (submitted) {
      event.preventDefault();
      return;
    }
    submitted = true;
    button.textContent = form.dataset.submitOnce;
    button.setAttribute("aria-busy", "true");
  });
  // 用瀏覽器「上一頁」回來時，頁面可能是快取的，要恢復可送出狀態
  window.addEventListener("pageshow", () => {
    submitted = false;
    button.textContent = label;
    button.removeAttribute("aria-busy");
  });
});
