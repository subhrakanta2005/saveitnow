import { useState } from 'react';
import { fetchMediaInfo, fetchDownloadUrl } from '../utils/api';
import MediaResult from '../components/MediaResult';
import './PlatformPage.css';

const PLATFORM_CONFIG = {
  instagram: {
    name: 'Instagram',
    icon: '📸',
    color: '#E1306C',
    gradient: 'linear-gradient(135deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888)',
    placeholder: 'Paste Instagram link — reel, post, story, profile...',
    types: [
      { label: '🎬 Reel', hint: 'instagram.com/reel/...' },
      { label: '📷 Post', hint: 'instagram.com/p/...' },
      { label: '📖 Story', hint: 'instagram.com/stories/...' },
      { label: '🖼 Profile Pic', hint: 'instagram.com/username/' },
    ],
    tips: [
      'Copy the link from the Instagram app — tap ··· → Copy Link',
      'Only public accounts are supported',
      'For stories, copy the story link while viewing it',
    ],
  },
  youtube: {
    name: 'YouTube',
    icon: '▶️',
    color: '#FF0000',
    gradient: 'linear-gradient(135deg, #FF0000, #cc0000)',
    placeholder: 'Paste YouTube link — video, short, playlist...',
    types: [
      { label: '🎥 Video', hint: 'youtube.com/watch?v=...' },
      { label: '⚡ Short', hint: 'youtube.com/shorts/...' },
      { label: '🎵 Audio', hint: 'Any YouTube URL' },
      { label: '🖼 Thumbnail', hint: 'Any YouTube URL' },
    ],
    tips: [
      'For audio only, select MP3 after fetching',
      'Supports videos up to 4K quality',
      'Playlists: paste individual video URLs',
    ],
  },
  tiktok: {
    name: 'TikTok',
    icon: '🎵',
    color: '#69C9D0',
    gradient: 'linear-gradient(135deg, #010101, #69C9D0)',
    placeholder: 'Paste TikTok video link...',
    types: [
      { label: '🎬 Video', hint: 'tiktok.com/@user/video/...' },
      { label: '🎵 Audio', hint: 'Any TikTok URL' },
    ],
    tips: [
      'Downloads without watermark',
      'Copy link from TikTok app — tap Share → Copy Link',
      'Supports HD quality',
    ],
  },
  twitter: {
    name: 'Twitter / X',
    icon: '𝕏',
    color: '#1DA1F2',
    gradient: 'linear-gradient(135deg, #1DA1F2, #0d8bd9)',
    placeholder: 'Paste Twitter / X post link...',
    types: [
      { label: '🎥 Video', hint: 'x.com/user/status/...' },
      { label: '🎞 GIF', hint: 'x.com/user/status/...' },
      { label: '🖼 Image', hint: 'x.com/user/status/...' },
    ],
    tips: [
      'Copy the tweet URL from your browser or app',
      'Works for both twitter.com and x.com links',
      'GIFs are downloaded as MP4',
    ],
  },
  facebook: {
    name: 'Facebook',
    icon: '📘',
    color: '#1877F2',
    gradient: 'linear-gradient(135deg, #1877F2, #0d65d9)',
    placeholder: 'Paste Facebook video link...',
    types: [
      { label: '🎥 Video', hint: 'facebook.com/watch?v=...' },
      { label: '🎬 Reel', hint: 'facebook.com/reel/...' },
    ],
    tips: [
      'Only public videos are supported',
      'Copy link from Facebook — tap ··· → Copy Link',
      'HD quality available when the video has it',
    ],
  },
  reddit: {
    name: 'Reddit',
    icon: '🤖',
    color: '#FF4500',
    gradient: 'linear-gradient(135deg, #FF4500, #cc3700)',
    placeholder: 'Paste Reddit post link...',
    types: [
      { label: '🎥 Video', hint: 'reddit.com/r/sub/comments/...' },
      { label: '🎞 GIF', hint: 'reddit.com/r/sub/comments/...' },
    ],
    tips: [
      'Supports all subreddit video posts',
      'Copy the full post URL from your browser',
      'Works with v.redd.it links too',
    ],
  },
  pinterest: {
    name: 'Pinterest',
    icon: '📌',
    color: '#E60023',
    gradient: 'linear-gradient(135deg, #E60023, #b5001c)',
    placeholder: 'Paste Pinterest pin link...',
    types: [
      { label: '🎥 Video', hint: 'pinterest.com/pin/...' },
      { label: '🖼 Image', hint: 'pinterest.com/pin/...' },
    ],
    tips: [
      'Copy the pin URL from your browser',
      'Supports both videos and high-res images',
      'Works with pin.it short links too',
    ],
  },
};

export default function PlatformPage({ platform }) {
  const config = PLATFORM_CONFIG[platform];
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [activeType, setActiveType] = useState(0);

  const handleFetch = async (e) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await fetchMediaInfo(trimmed);
      setResult(data);
    } catch (err) {
      setError(err.message || 'Something went wrong. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (formatId, title, ext) => {
    try {
      if (formatId.startsWith('http')) {
        const a = document.createElement('a');
        a.href = formatId;
        a.download = `${title || 'media'}.${ext || 'mp4'}`;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        return;
      }
      const data = await fetchDownloadUrl(url, formatId);
      const a = document.createElement('a');
      a.href = data.download_url;
      a.download = `${data.title || title || 'media'}.${ext || 'mp4'}`;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err) {
      setError(err.message || 'Download failed. Try again.');
    }
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text.startsWith('http')) {
        setUrl(text);
      }
    } catch {
      // clipboard not available
    }
  };

  return (
    <div className="platform-page">
      <div className="pp-blob" style={{ background: `radial-gradient(circle, ${config.color}22 0%, transparent 70%)` }} />

      {/* Header */}
      <div className="pp-header">
        <div className="pp-icon-wrap" style={{ background: config.gradient }}>
          <span className="pp-icon">{config.icon}</span>
        </div>
        <h1 className="pp-title">{config.name} <span className="grad-text">Downloader</span></h1>
        <p className="pp-sub">Download {config.name} content free, fast and without login</p>
      </div>

      {/* Type selector */}
      <div className="pp-types">
        {config.types.map((t, i) => (
          <button
            key={i}
            className={`pp-type-btn ${activeType === i ? 'active' : ''}`}
            style={{ '--c': config.color }}
            onClick={() => setActiveType(i)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="pp-input-section">
        <form onSubmit={handleFetch} className="pp-form">
          <div className="pp-input-wrap" style={{ '--c': config.color }}>
            <input
              className="pp-input"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder={config.types[activeType].hint || config.placeholder}
              autoComplete="off"
              autoFocus
            />
            {!url && (
              <button type="button" className="pp-paste-btn" onClick={handlePaste}
                style={{ background: config.gradient }}>
                📋 Paste
              </button>
            )}
            {url && (
              <button type="submit" className="pp-dl-btn" disabled={loading}
                style={{ background: config.gradient }}>
                {loading
                  ? <><span className="btn-spinner" /> Fetching…</>
                  : '⬇ Download'}
              </button>
            )}
          </div>
        </form>

        {error && (
          <div className="pp-error">⚠️ {error}</div>
        )}

        {result && (
          <MediaResult
            data={result}
            onDownload={handleDownload}
            color={config.color}
          />
        )}
      </div>

      {/* Tips */}
      <div className="pp-tips">
        <div className="pp-tips-title">💡 Tips for {config.name}</div>
        <ul className="pp-tips-list">
          {config.tips.map((tip, i) => (
            <li key={i}>{tip}</li>
          ))}
        </ul>
      </div>

      {/* FAQ */}
      <div className="pp-faq">
        <h2 className="section-title" style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>
          How to download from {config.name}?
        </h2>
        <div className="faq-steps">
          <div className="faq-step">
            <span className="faq-num" style={{ color: config.color }}>1</span>
            <span>Open {config.name} and find the content you want to download</span>
          </div>
          <div className="faq-step">
            <span className="faq-num" style={{ color: config.color }}>2</span>
            <span>Tap the Share button → Copy Link</span>
          </div>
          <div className="faq-step">
            <span className="faq-num" style={{ color: config.color }}>3</span>
            <span>Paste the link above and click Download</span>
          </div>
          <div className="faq-step">
            <span className="faq-num" style={{ color: config.color }}>4</span>
            <span>Choose your quality and save the file</span>
          </div>
        </div>
      </div>
    </div>
  );
}
