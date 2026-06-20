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
