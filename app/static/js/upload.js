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
  const form = document.querySelector('form[enctype="multipart/form-data"]');
  const progress = document.querySelector("#upload-progress");
  if (form && progress) form.addEventListener("submit", async (event) => {
    const file = input && input.files && input.files[0];
    if (!file || typeof uploadInChunks !== "function") return;
    event.preventDefault();
    progress.classList.remove("d-none");
    progress.setAttribute("aria-label", "视频上传进度");
    progress.value = 0;
    window.onUploadProgress = (value) => { progress.value = value; const label = document.querySelector('#upload-progress-label'); if (label) label.textContent = `${Math.round(value)}%`; };
    try {
      const metadata = {
        report_id: form.querySelector('[name="report_id"]')?.value || "api",
        title: form.querySelector('[name="title"]')?.value || file.name,
        description: form.querySelector('[name="description"]')?.value || ""
      };
      const result = await uploadInChunks(file, null, metadata);
      form.querySelector('input[type="submit"]').disabled = true;
      window.location.href = `/videos/${result.id}`;
    } catch (error) {
      progress.classList.add("d-none");
      alert(`上传失败：${error.message}`);
    }
  });
});
