import { Link } from 'react-router-dom';
import './Navbar.css';

export default function Navbar() {
  return (
    <nav className="navbar">
      <Link to="/" className="logo">SaveItNow.in</Link>
      <div className="nav-links">
        <Link to="/about" className="nav-link">About</Link>
        <Link to="/how-it-works" className="nav-link">How it works</Link>
        <div className="nav-badge">1000+ sites</div>
      </div>
    </nav>
  );
}
