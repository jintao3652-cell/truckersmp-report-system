document.addEventListener("DOMContentLoaded", () => {
  const input = document.querySelector('input[type="file"]');
  const button = document.querySelector("#choose-video");
  const label = document.querySelector("#selected-video");
  if (input && button) {
    button.addEventListener("click", () => input.click());
    input.addEventListener("change", () => {
      const file = input.files && input.files[0];
      if (!file) {
        label.textContent = "尚未选择文件";
        return;
      }
      const size = file.size < 1024 * 1024
        ? `${(file.size / 1024).toFixed(1)} KB`
        : `${(file.size / 1024 / 1024).toFixed(1)} MB`;
      label.textContent = `${file.name} (${size})`;
    });
  }
});
