import { useState } from 'react';
import { fetchDownloadUrl } from '../utils/api';
import './MediaResult.css';

const PLATFORM_EMOJI = {
  instagram: '📸', youtube: '▶️', tiktok: '🎵',
  twitter: '🐦', facebook: '👥', reddit: '💬',
  pinterest: '📌', other: '🌐',
};

function formatDuration(secs) {
  if (!secs) return null;
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export default function MediaResult({ info, url }) {
  const [selectedIdx, setSelectedIdx] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  const fmt = selectedIdx !== null ? info.formats[selectedIdx] : null;
  const dur = formatDuration(info.duration);

  const handleDownload = async () => {
    if (!fmt) return;
    setDownloading(true);
    setError('');
    try {
      const data = await fetchDownloadUrl(url, fmt.format_id);
      const a = document.createElement('a');
      a.href = data.download_url;
      a.target = '_blank';
      a.download = `${data.title || 'saveitnow'}.${fmt.ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setDone(true);
      setTimeout(() => setDone(false), 3000);
    } catch (e) {
      setError(e.message);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="result-card">
      <div className="media-preview">
        {info.thumbnail ? (
          <img className="thumb" src={info.thumbnail} alt="thumbnail"
            onError={(e) => e.target.style.display = 'none'} />
        ) : (
          <div className="thumb-placeholder">
            {PLATFORM_EMOJI[info.platform] || '🎬'}
          </div>
        )}
        <div className="media-meta">
          <div className="media-title" title={info.title}>{info.title}</div>
          <div className="media-tags">
            <span className="tag tag-platform">{info.platform}</span>
            {dur && <span className="tag tag-duration">{dur}</span>}
          </div>
        </div>
      </div>

      <div className="formats-label">Choose quality</div>
      <div className="formats-grid">
        {info.formats.map((f, i) => (
          <button
            key={i}
            className={`fmt-btn ${selectedIdx === i ? 'selected' : ''}`}
            onClick={() => setSelectedIdx(i)}
          >
            <div className="fmt-label">{f.label}</div>
            <div className="fmt-ext">
              .{f.ext}
              {f.filesize ? ` · ${(f.filesize / 1048576).toFixed(1)} MB` : ''}
            </div>
          </button>
        ))}
      </div>

      {error && <div className="error-box">⚠️ {error}</div>}

      <button
        className="btn-download"
        onClick={handleDownload}
        disabled={selectedIdx === null || downloading}
      >
        {downloading ? (
          <><span className="dl-spinner" /> Preparing…</>
        ) : done ? (
          '✓ Download started!'
        ) : selectedIdx !== null ? (
          `Download ${fmt.label}`
        ) : (
          'Select a format to download'
        )}
      </button>
    </div>
  );
}
