import { useState } from 'react';
import './UrlInput.css';

export default function UrlInput({ onFetch, loading }) {
  const [url, setUrl] = useState('');

  const handleSubmit = () => {
    if (url.trim()) onFetch(url.trim());
  };

  return (
    <div className="input-wrap">
      <div className={`input-box ${url ? 'has-value' : ''}`}>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          placeholder="Paste a link — e.g. https://www.instagram.com/reel/..."
          autoComplete="off"
        />
        <button className="btn-fetch" onClick={handleSubmit} disabled={loading || !url.trim()}>
          {loading ? <span className="spinner" /> : 'Fetch'}
        </button>
      </div>
    </div>
  );
}
