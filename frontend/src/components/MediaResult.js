import { useState } from 'react';
import './MediaResult.css';

const PLATFORM_EMOJI = {
  instagram: '📸', youtube: '▶️', tiktok: '🎵',
  twitter: '🐦', facebook: '👥', reddit: '💬',
  pinterest: '📌', other: '🌐',
};

function formatDuration(secs) {
  if (!secs) return null;
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

export default function MediaResult({ data, onDownload, color }) {
  const [selectedIdx, setSelectedIdx] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [done, setDone] = useState(false);
  const [thumbError, setThumbError] = useState(false);

  if (!data) return null;

  const formats = data.formats || [];
  const fmt = selectedIdx !== null ? formats[selectedIdx] : null;
  const dur = formatDuration(data.duration);

  const handleDownloadClick = async () => {
    if (!fmt) return;
    setDownloading(true);
    try {
      await onDownload(fmt.format_id, data.title, fmt.ext);
      setDone(true);
      setTimeout(() => setDone(false), 3000);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="result-card">
      <div className="media-preview">
        {data.thumbnail && !thumbError ? (
          <img className="thumb" src={data.thumbnail} alt="thumbnail"
            onError={() => setThumbError(true)} />
        ) : (
          <div className="thumb-placeholder">
            {PLATFORM_EMOJI[data.platform] || '🎬'}
          </div>
        )}
        <div className="media-meta">
          <div className="media-title" title={data.title}>{data.title}</div>
          <div className="media-tags">
            <span className="tag tag-platform">{data.platform}</span>
            {dur && <span className="tag tag-duration">{dur}</span>}
          </div>
        </div>
      </div>

      <div className="formats-label">Choose quality</div>
      <div className="formats-grid">
        {formats.map((f, i) => (
          <button
            key={i}
            className={`fmt-btn ${selectedIdx === i ? 'selected' : ''}`}
            style={selectedIdx === i ? { borderColor: color } : undefined}
            onClick={() => setSelectedIdx(i)}
          >
            <div className="fmt-label">{f.label}</div>
            <div className="fmt-ext">
              .{f.ext}
              {f.filesize ? ` · ${f.filesize}` : ''}
            </div>
          </button>
        ))}
      </div>

      <button
        className="btn-download"
        style={selectedIdx !== null ? { background: color } : undefined}
        onClick={handleDownloadClick}
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
