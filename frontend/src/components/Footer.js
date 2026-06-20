import { Link } from 'react-router-dom';
import './Footer.css';

export default function Footer() {
  return (
    <footer className="footer">
      <span className="footer-logo">SaveItNow</span>
      <div>© {new Date().getFullYear()} SaveItNow.in · Free forever · No data stored</div>
      <div className="footer-links">
        <Link to="/">Home</Link>
        <Link to="/how-it-works">How it works</Link>
        <Link to="/about">About</Link>
      </div>
    </footer>
  );
}
