async function uploadInChunks(file, token, metadata = {}, chunkSize = 8 * 1024 * 1024) {
  const auth = token ? {Authorization: `Bearer ${token}`} : {};
  const resumeKey = `upload-session:${file.name}:${file.size}:${file.lastModified}`;
  const resumeId = localStorage.getItem(resumeKey);
  const init = await fetch("/api/v1/uploads", {method: "POST", headers: {...auth, "Content-Type": "application/json"}, body: JSON.stringify({filename: file.name, size: file.size, resume_id: resumeId, ...metadata})});
  if (!init.ok) throw new Error((await init.json()).error || "upload init failed");
  const session = await init.json();
  localStorage.setItem(resumeKey, session.id);
  let offset = Number(session.received_size || 0);
  while (offset < file.size) {
    const chunk = file.slice(offset, Math.min(offset + chunkSize, file.size));
    let response;
    for (let attempt = 0; attempt < 4; attempt++) {
      try {
        response = await fetch(`/api/v1/uploads/${session.id}?offset=${offset}`, {method: "PUT", headers: auth, body: chunk});
        if (response.ok) break;
      } catch (_) {}
      await new Promise(resolve => setTimeout(resolve, 500 * 2 ** attempt));
    }
    if (!response?.ok) throw new Error((await response?.json?.() || {}).error || "chunk upload failed");
    offset = (await response.json()).received_size;
    localStorage.setItem(resumeKey, session.id);
    if (typeof window.onUploadProgress === "function") window.onUploadProgress(offset / file.size * 100);
  }
  const done = await fetch(`/api/v1/uploads/${session.id}/complete`, {method: "POST", headers: auth});
  if (!done.ok) throw new Error((await done.json()).error || "upload completion failed");
  localStorage.removeItem(resumeKey);
  return done.json();
}

window.startChunkUpload = async function (file, metadata) {
  const progress = document.querySelector("#upload-progress");
  if (progress) progress.classList.remove("d-none");
  window.onUploadProgress = value => { if (progress) progress.value = value; };
  return uploadInChunks(file, null, metadata);
};
