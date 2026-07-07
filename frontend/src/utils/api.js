const API_BASE = process.env.REACT_APP_API_URL || 'https://saveitnow-api.onrender.com';

export const fetchMediaInfo = async (url) => {
  const res = await fetch(`${API_BASE}/info`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to fetch media info');
  }
  return res.json();
};

export const fetchDownloadUrl = async (url, format_id) => {
  const res = await fetch(`${API_BASE}/download?format_id=${encodeURIComponent(format_id)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Download failed');
  }
  return res.json();
};

// Builds a URL to our own backend that streams a direct CDN media URL
// back with a Content-Disposition header, so the browser actually saves
// the file. Needed because the `download` attribute on an <a> tag is
// ignored by browsers for cross-origin URLs (e.g. Instagram/YouTube/
// Facebook CDN links) — fetching it through our own origin fixes that.
export const buildProxyDownloadUrl = (directUrl, filename, ext) => {
  const params = new URLSearchParams({
    url: directUrl,
    filename: filename || 'media',
    ext: ext || 'mp4',
  });
  return `${API_BASE}/proxy/download?${params.toString()}`;
};


