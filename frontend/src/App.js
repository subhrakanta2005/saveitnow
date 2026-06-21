import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Home from './pages/Home';
import About from './pages/About';
import HowItWorks from './pages/HowItWorks';
import PlatformPage from './pages/PlatformPage';
import './styles/global.css';

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
        <Route path="/how-it-works" element={<HowItWorks />} />
        <Route path="/instagram" element={<PlatformPage platform="instagram" />} />
        <Route path="/youtube" element={<PlatformPage platform="youtube" />} />
        <Route path="/tiktok" element={<PlatformPage platform="tiktok" />} />
        <Route path="/twitter" element={<PlatformPage platform="twitter" />} />
        <Route path="/facebook" element={<PlatformPage platform="facebook" />} />
        <Route path="/reddit" element={<PlatformPage platform="reddit" />} />
        <Route path="/pinterest" element={<PlatformPage platform="pinterest" />} />
      </Routes>
      <Footer />
    </BrowserRouter>
  );
}
