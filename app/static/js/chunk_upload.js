async function uploadInChunks(file, token, metadata = {}, chunkSize = 8 * 1024 * 1024) {
  const headers = {"Content-Type": "application/json"};
  if (token) headers.Authorization = `Bearer ${token}`;
  const init = await fetch("/api/v1/uploads", {method: "POST", headers, body: JSON.stringify({filename: file.name, size: file.size, ...metadata})});
  if (!init.ok) throw new Error((await init.json()).error || "upload init failed");
  const session = await init.json();
  let offset = 0;
  while (offset < file.size) {
    const chunk = file.slice(offset, Math.min(offset + chunkSize, file.size));
    const response = await fetch(`/api/v1/uploads/${session.id}?offset=${offset}`, {method: "PUT", headers: token ? {Authorization: `Bearer ${token}`} : {}, body: chunk});
    if (!response.ok) throw new Error((await response.json()).error || "chunk upload failed");
    offset = (await response.json()).received_size;
    if (typeof window.onUploadProgress === "function") window.onUploadProgress(offset / file.size * 100);
  }
  const done = await fetch(`/api/v1/uploads/${session.id}/complete`, {method: "POST", headers: token ? {Authorization: `Bearer ${token}`} : {}});
  if (!done.ok) throw new Error((await done.json()).error || "upload completion failed");
  return done.json();
}
