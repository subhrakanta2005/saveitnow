import { useNavigate } from 'react-router-dom';
import './Home.css';

const PLATFORMS = [
  {
    id: 'instagram',
    name: 'Instagram',
    icon: '📸',
    color: '#E1306C',
    gradient: 'linear-gradient(135deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888)',
    desc: 'Reels, Posts, Stories, Highlights, Profile Pictures',
    types: ['Reels', 'Posts', 'Stories', 'Highlights', 'Profile Pic'],
  },
  {
    id: 'youtube',
    name: 'YouTube',
    icon: '▶️',
    color: '#FF0000',
    gradient: 'linear-gradient(135deg, #FF0000, #cc0000)',
    desc: 'Videos, Shorts, Playlists, Thumbnails, Audio',
    types: ['Videos', 'Shorts', 'Audio (MP3)', 'Thumbnails'],
  },
  {
    id: 'tiktok',
    name: 'TikTok',
    icon: '🎵',
    color: '#010101',
    gradient: 'linear-gradient(135deg, #010101, #69C9D0)',
    desc: 'Videos without watermark, Audio',
    types: ['Videos', 'Audio'],
  },
  {
    id: 'twitter',
    name: 'Twitter / X',
    icon: '𝕏',
    color: '#1DA1F2',
    gradient: 'linear-gradient(135deg, #1DA1F2, #0d8bd9)',
    desc: 'Videos, GIFs, Images from tweets',
    types: ['Videos', 'GIFs', 'Images'],
  },
  {
    id: 'facebook',
    name: 'Facebook',
    icon: '📘',
    color: '#1877F2',
    gradient: 'linear-gradient(135deg, #1877F2, #0d65d9)',
    desc: 'Videos, Reels, Stories',
    types: ['Videos', 'Reels', 'Stories'],
  },
  {
    id: 'reddit',
    name: 'Reddit',
    icon: '🤖',
    color: '#FF4500',
    gradient: 'linear-gradient(135deg, #FF4500, #cc3700)',
    desc: 'Videos, GIFs from any subreddit',
    types: ['Videos', 'GIFs'],
  },
  {
    id: 'pinterest',
    name: 'Pinterest',
    icon: '📌',
    color: '#E60023',
    gradient: 'linear-gradient(135deg, #E60023, #b5001c)',
    desc: 'Videos, Images, GIFs',
    types: ['Videos', 'Images', 'GIFs'],
  },
];

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="home">
      <div className="blob blob-1" />
      <div className="blob blob-2" />
      <div className="blob blob-3" />

      <div className="hero">
        <div className="hero-eyebrow"><span className="dot" />1000+ platforms supported</div>
        <h1>
          Download <span className="grad-text">anything</span><br />
          from anywhere.
        </h1>
        <p className="hero-sub">
          Choose your platform below and download videos, reels, stories,
          audio and more — free, fast, no login required.
        </p>
      </div>

      <div className="platforms-grid">
        {PLATFORMS.map((p) => (
          <div
            key={p.id}
            className="platform-card"
            onClick={() => navigate(`/${p.id}`)}
            style={{ '--platform-color': p.color }}
          >
            <div className="platform-icon-wrap" style={{ background: p.gradient }}>
              <span className="platform-icon">{p.icon}</span>
            </div>
            <div className="platform-info">
              <h3 className="platform-name">{p.name}</h3>
              <p className="platform-desc">{p.desc}</p>
              <div className="platform-types">
                {p.types.map(t => (
                  <span key={t} className="type-pill">{t}</span>
                ))}
              </div>
            </div>
            <div className="platform-arrow">→</div>
          </div>
        ))}
      </div>

      <div className="how-section">
        <div className="section-label">How it works</div>
        <h2 className="section-title">Three steps. That's it.</h2>
        <div className="steps">
          <div className="step">
            <div className="step-num grad-text">01</div>
            <div className="step-title">Choose platform</div>
            <div className="step-desc">Select Instagram, YouTube, TikTok or any other platform from above.</div>
          </div>
          <div className="step">
            <div className="step-num grad-text">02</div>
            <div className="step-title">Paste the link</div>
            <div className="step-desc">Copy the URL from the app or browser and paste it in the input box.</div>
          </div>
          <div className="step">
            <div className="step-num grad-text">03</div>
            <div className="step-title">Download</div>
            <div className="step-desc">Choose your quality and hit download. Done in seconds.</div>
          </div>
        </div>
      </div>
    </div>
  );
}
