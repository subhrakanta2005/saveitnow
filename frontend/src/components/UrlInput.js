import { useState, useRef } from 'react';
import './UrlInput.css';

export default function UrlInput({ onFetch, loading }) {
  const [url, setUrl] = useState('');
  const inputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) { inputRef.current?.focus(); return; }
    onFetch(trimmed);
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text.startsWith('http')) {
        setUrl(text);
        onFetch(text.trim());
      }
    } catch {
      inputRef.current?.focus();
    }
  };

  return (
    <form className="url-form" onSubmit={handleSubmit}>
      <div className="input-wrap">
        <input
          ref={inputRef}
          className="url-input"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste link — instagram.com, youtube.com, tiktok.com..."
          autoComplete="off"
          autoFocus
        />
        {url ? (
          <button className="btn-fetch" type="submit" disabled={loading}>
            {loading ? <><span className="fetch-spinner" /> Fetching…</> : '⬇ Download'}
          </button>
        ) : (
          <button className="btn-fetch" type="button" onClick={handlePaste} disabled={loading}>
            📋 Paste
          </button>
        )}
      </div>
      <p className="paste-hint">Press <kbd>Ctrl</kbd>+<kbd>V</kbd> to paste, then hit Enter</p>
    </form>
  );
}
