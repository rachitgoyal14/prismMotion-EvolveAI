import React, { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';
import { NavItem } from '../types';
import { useNavigate, useLocation } from 'react-router-dom';

const navItems: NavItem[] = [
  { label: 'Home', href: '/' },
  { label: 'About Us', href: '/#technology' },
  { label: 'Featured Project', href: '/#projects' },
  { label: 'Contact Us', href: '/#contact' },
];

const Navbar: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleNavigation = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    e.preventDefault();
    setMobileMenuOpen(false);

    if (href === '/') {
      if (location.pathname !== '/') {
        navigate('/');
      } else {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
      return;
    }

    if (href.startsWith('/#')) {
      const id = href.replace('/#', '');
      if (location.pathname !== '/') {
        navigate('/');
        // Wait for navigation then scroll
        setTimeout(() => {
          const element = document.getElementById(id);
          element?.scrollIntoView({ behavior: 'smooth' });
        }, 100);
      } else {
        const element = document.getElementById(id);
        element?.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  return (
    <nav className={`fixed top-0 left-0 w-full z-50 transition-all duration-300 ${scrolled ? 'bg-[#f8fcf9]/80 backdrop-blur-md shadow-sm py-4' : 'bg-transparent py-6'}`}>
      {/* Added larger horizontal padding (px-8 md:px-16) for the requested margins */}
      <div className="w-full px-8 md:px-16 flex justify-between items-center">

        {/* Logo Section */}
        <div className="flex-shrink-0 flex items-center">
          <span
            className="text-2xl font-black tracking-tighter text-black cursor-pointer"
            onClick={() => navigate('/')}
          >
            PRISM <span className="text-emerald-600">MOTION</span>
          </span>
        </div>

        {/* Center Nav Items (Desktop) */}
        <div className="hidden md:flex absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 items-center space-x-8">
          {navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              onClick={(e) => handleNavigation(e, item.href)}
              className="text-base font-semibold text-black hover:text-emerald-600 transition-colors"
            >
              {item.label}
            </a>
          ))}
        </div>

        {/* Right Side: Auth Buttons (Desktop) */}
        <div className="hidden md:flex items-center space-x-6">
          <button className="text-sm font-bold text-black hover:text-emerald-600 transition-colors">
            Login
          </button>
          <button className="bg-black text-white px-6 py-2.5 rounded-full font-bold hover:bg-emerald-600 hover:text-white transition-all active:scale-95 text-sm shadow-lg">
            Sign Up
          </button>
        </div>

        {/* Mobile Toggle */}
        <button
          className="md:hidden text-black z-50 relative"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 bg-[#f8fcf9] z-40 flex flex-col items-center justify-center space-y-8 md:hidden">
          {navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              onClick={(e) => handleNavigation(e, item.href)}
              className="text-2xl font-bold text-gray-900"
            >
              {item.label}
            </a>
          ))}
          <div className="flex flex-col space-y-4 w-64 pt-8">
            <button className="text-lg font-bold text-black">
              Login
            </button>
            <button className="bg-black text-white w-full py-4 rounded-full font-bold text-lg">
              Sign Up
            </button>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;