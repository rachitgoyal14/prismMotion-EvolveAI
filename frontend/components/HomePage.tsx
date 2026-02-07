import React from 'react';
import { ArrowRight } from 'lucide-react';
import Navbar from './Navbar';
import Hero from './Hero';
import Features from './Features';
import FeaturedProjects from './FeaturedProjects';
import { useNavigate } from 'react-router-dom';

const HomePage = () => {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen bg-[#f8fcf9] text-gray-900 selection:bg-emerald-200 selection:text-emerald-900">
            <Navbar />
            <main>
                {/* Pass callback to switch to onboarding */}
                <Hero onStart={() => navigate('/onboarding')} />
                <Features />
                <FeaturedProjects />
            </main>

            {/* Redesigned Footer */}
            <footer className="bg-[#006838] text-white py-20 md:py-32 relative overflow-hidden" id="contact">
                <div className="container mx-auto px-8 md:px-16">
                    <div className="flex flex-col lg:flex-row justify-between gap-16 lg:gap-24">

                        {/* Left Section (Primary Content) */}
                        <div className="flex-1 max-w-2xl">
                            <h2 className="text-4xl md:text-6xl font-medium tracking-tight mb-6 leading-[1.1]">
                                Let’s build the future of pharma engagement.
                            </h2>
                            <p className="text-lg md:text-xl text-white/80 mb-10 font-light leading-relaxed max-w-lg">
                                Have an idea? Let’s create AI-powered video experiences for your next pharma engagement project.
                            </p>

                            <div className="relative max-w-md group">
                                <input
                                    type="email"
                                    placeholder="Enter your email…"
                                    className="w-full bg-transparent border-b border-white/40 py-4 pr-12 text-lg text-white placeholder-white/50 focus:outline-none focus:border-white transition-colors"
                                />
                                <button className="absolute right-0 top-1/2 -translate-y-1/2 text-white/70 hover:text-white transition-colors">
                                    <ArrowRight size={24} />
                                </button>
                            </div>
                        </div>

                        {/* Right Section (Navigation Content) */}
                        <div className="flex gap-16 md:gap-32">
                            {/* Column 1 - Sitemap */}
                            <div className="flex flex-col space-y-4">
                                <h3 className="text-sm font-bold uppercase tracking-widest text-white/40 mb-2">Sitemap</h3>
                                <a href="#" className="text-lg hover:text-emerald-300 transition-colors">Home</a>
                                <a href="#about" className="text-lg hover:text-emerald-300 transition-colors">About Us</a>
                                <a href="#projects" className="text-lg hover:text-emerald-300 transition-colors">Featured Projects</a>
                                <a href="#faq" className="text-lg hover:text-emerald-300 transition-colors">FAQ</a>
                                <a href="#contact" className="text-lg hover:text-emerald-300 transition-colors">Contact</a>
                            </div>

                            {/* Column 2 - Social */}
                            <div className="flex flex-col space-y-4">
                                <h3 className="text-sm font-bold uppercase tracking-widest text-white/40 mb-2">Social</h3>
                                <a href="#" className="text-lg hover:text-emerald-300 transition-colors">Twitter</a>
                                <a href="#" className="text-lg hover:text-emerald-300 transition-colors">Instagram</a>
                                <a href="#" className="text-lg hover:text-emerald-300 transition-colors">LinkedIn</a>
                            </div>
                        </div>
                    </div>

                    {/* Bottom Row (Footer Base) */}
                    <div className="border-t border-white/10 mt-20 pt-8 flex flex-col md:flex-row justify-between items-center text-sm text-white/40 gap-4">
                        <div>
                            &copy; 2026 Prism Motion. All rights reserved.
                        </div>
                        <div className="font-medium tracking-wide">
                            Made with Prism Motion
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
};

export default HomePage;
