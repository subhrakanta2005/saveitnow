import { useState } from 'react';
import UrlInput from '../components/UrlInput';
import MediaResult from '../components/MediaResult';
import { fetchMediaInfo } from '../utils/api';
import './Home.css';

const PLATFORMS = [
  { icon: '📸', name: 'Instagram' },
  { icon: '▶️', name: 'YouTube' },
  { icon: '🎵', name: 'TikTok' },
  { icon: '🐦', name: 'Twitter / X' },
  { icon: '👥', name: 'Facebook' },
  { icon: '📌', name: 'Pinterest' },
  { icon: '💬', name: 'Reddit' },
  { icon: '+', name: '1000 more' },
];

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [mediaInfo, setMediaInfo] = useState(null);
  const [currentUrl, setCurrentUrl] = useState('');
  const [error, setError] = useState('');

  const handleFetch = async (url) => {
    setLoading(true);
    setError('');
    setMediaInfo(null);
    setCurrentUrl(url);
    try {
      const info = await fetchMediaInfo(url);
      setMediaInfo(info);
    } catch (e) {
      setError(e.message || 'Something went wrong. Check the URL and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="home">
      {/* Ambient blobs */}
      <div className="blob blob-1" />
      <div className="blob blob-2" />
      <div className="blob blob-3" />

      {/* Hero */}
      <section className="hero">
        <div className="hero-eyebrow">
          <span className="dot" />
          Free · No signup · No limits
        </div>
        <h1>Download <span className="grad-text">anything</span><br />from anywhere.</h1>
        <p className="hero-sub">
          Paste a link from Instagram, YouTube, TikTok, Twitter, Facebook, Reddit,
          and 1000+ more sites. Get your media in seconds.
        </p>

        <UrlInput onFetch={handleFetch} loading={loading} />

        <div className="platforms">
          {PLATFORMS.map((p) => (
            <div key={p.name} className="platform-badge">
              <span>{p.icon}</span> {p.name}
            </div>
          ))}
        </div>
      </section>

      {/* Result */}
      <section className="result-section">
        {loading && (
          <div className="loading-box">
            <span className="big-spinner" />
            <span>Analysing link…</span>
          </div>
        )}
        {error && <div className="error-box">⚠️ {error}</div>}
        {mediaInfo && <MediaResult info={mediaInfo} url={currentUrl} />}
      </section>

      {/* How it works */}
      <section className="how-section">
        <div className="section-label">How it works</div>
        <h2 className="section-title">Three steps. That's it.</h2>
        <div className="steps">
          {[
            { num: '01', color: 'linear-gradient(135deg,#7c3aed,#ec4899)', title: 'Paste the link', desc: 'Copy any video, reel, story, or post URL and paste it above.' },
            { num: '02', color: 'linear-gradient(135deg,#ec4899,#06b6d4)', title: 'Pick your format', desc: 'Choose the quality — 1080p, 720p, 480p, or audio-only MP3.' },
            { num: '03', color: 'linear-gradient(135deg,#06b6d4,#7c3aed)', title: 'Save it now', desc: 'Hit download. The file goes straight to your device.' },
          ].map((s) => (
            <div key={s.num} className="step">
              <div className="step-num" style={{ background: s.color, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{s.num}</div>
              <div className="step-title">{s.title}</div>
              <div className="step-desc">{s.desc}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
