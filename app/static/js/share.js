document.querySelector('#share-video')?.addEventListener('click', async (event) => {
  const url = event.currentTarget.dataset.shareUrl;
  try {
    await navigator.clipboard.writeText(url);
    document.querySelector('#share-status').textContent = '分享链接已复制';
  } catch (_) {
    window.prompt('复制此分享链接', url);
  }
});
