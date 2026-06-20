import { Link, useLocation } from 'react-router-dom';
import './Navbar.css';

export default function Navbar() {
  const { pathname } = useLocation();
  return (
    <nav className="navbar">
      <Link to="/" className="nav-logo">SaveItNow</Link>
      <div className="nav-links">
        <Link to="/" className={`nav-link ${pathname === '/' ? 'active' : ''}`}>Home</Link>
        <Link to="/how-it-works" className={`nav-link ${pathname === '/how-it-works' ? 'active' : ''}`}>How it works</Link>
        <Link to="/about" className={`nav-link ${pathname === '/about' ? 'active' : ''}`}>About</Link>
      </div>
      <div className="nav-badge">Free · No Login</div>
    </nav>
  );
}
