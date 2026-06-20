import './HowItWorks.css';

const STEPS = [
  {
    num: '01',
    color: 'linear-gradient(135deg,#7c3aed,#ec4899)',
    title: 'Copy the URL',
    desc: 'Go to any platform — Instagram, YouTube, TikTok, etc. Find the video or post you want to save. Copy the link from your browser or the share button.',
  },
  {
    num: '02',
    color: 'linear-gradient(135deg,#ec4899,#06b6d4)',
    title: 'Paste and fetch',
    desc: 'Head back to SaveItNow, paste the link into the input field, and hit Fetch. Our server will grab the available formats instantly.',
  },
  {
    num: '03',
    color: 'linear-gradient(135deg,#06b6d4,#a78bfa)',
    title: 'Pick your quality',
    desc: 'Choose from available resolutions — 1080p, 720p, 480p, 360p, or audio-only MP3. Pick what fits your needs.',
  },
  {
    num: '04',
    color: 'linear-gradient(135deg,#a78bfa,#7c3aed)',
    title: 'Download',
    desc: 'Hit the Download button. The file starts downloading directly to your device — no detours, no waiting.',
  },
];

export default function HowItWorks() {
  return (
    <div className="hiw-page">
      <div className="hiw-container">
        <div className="hiw-eyebrow">How it works</div>
        <h1 className="hiw-title">Simple as <span className="grad-text">1-2-3-4.</span></h1>
        <div className="hiw-steps">
          {STEPS.map((s) => (
            <div key={s.num} className="hiw-step">
              <div className="hiw-num" style={{ background: s.color, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                {s.num}
              </div>
              <div className="hiw-content">
                <div className="hiw-step-title">{s.title}</div>
                <div className="hiw-step-desc">{s.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
