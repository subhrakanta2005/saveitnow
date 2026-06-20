import './About.css';

export default function About() {
  return (
    <div className="about-page">
      <div className="about-container">
        <div className="about-eyebrow">About</div>
        <h1 className="about-title">Built to save your media,<br /><span className="grad-text">instantly.</span></h1>
        <p className="about-desc">
          SaveItNow is a free, no-signup tool that lets you download videos, reels,
          stories, and images from over 1000 platforms — including Instagram, YouTube,
          TikTok, Twitter, Facebook, Reddit, and more.
        </p>
        <div className="about-cards">
          <div className="about-card">
            <div className="about-card-icon">⚡</div>
            <div className="about-card-title">Fast</div>
            <div className="about-card-desc">No waiting. Paste, fetch, download — all in seconds.</div>
          </div>
          <div className="about-card">
            <div className="about-card-icon">🔒</div>
            <div className="about-card-title">Private</div>
            <div className="about-card-desc">We don't store your URLs or media. Nothing is saved on our servers.</div>
          </div>
          <div className="about-card">
            <div className="about-card-icon">🌍</div>
            <div className="about-card-title">Universal</div>
            <div className="about-card-desc">1000+ supported sites powered by yt-dlp under the hood.</div>
          </div>
        </div>
        <p className="about-note">
          ⚠️ For personal use only. Please respect content creators and platform terms of service.
        </p>
      </div>
    </div>
  );
}
