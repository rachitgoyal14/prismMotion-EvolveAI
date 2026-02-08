import React, { useState, useRef, useEffect } from 'react';
import { ArrowLeft, ArrowRight, Check, Upload, X, Image as ImageIcon, FileText, Globe, Mail, Paperclip } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface OnboardingProps {
  onFinish: (data: any) => void;
}

const steps = [
  { id: 1, label: 'Company' },
  { id: 2, label: 'Contact' },
  { id: 3, label: 'Context' },
  { id: 4, label: 'Assets' },
];

const Onboarding: React.FC<OnboardingProps> = ({ onFinish }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    companyName: '',
    website: '',
    email: '',
    context: '',
    contextFile: null as File | null,
    logo: null as File | null,
    assets: [] as File[],
  });

  const [scrapedData, setScrapedData] = useState<any>(null);
  const [isScraping, setIsScraping] = useState(false);

  const contextFileRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseRef = useRef({ x: 0, y: 0 });

  // Interactive Background Animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = window.innerWidth;
    let height = window.innerHeight;

    // Initialize mouse position to center
    mouseRef.current = { x: width / 2, y: height / 2 };

    const handleResize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
    };

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('mousemove', handleMouseMove);

    // Initial setup
    handleResize();

    let time = 0;

    // Smooth mouse interpolation
    let currentMouseX = width / 2;
    let currentMouseY = height / 2;

    const animate = () => {
      time += 0.008; // Gentle breathing speed

      // Lerp mouse position for smoothness
      currentMouseX += (mouseRef.current.x - currentMouseX) * 0.05;
      currentMouseY += (mouseRef.current.y - currentMouseY) * 0.05;

      // 1. Clear Canvas (Transparent) - Allows bg-[#e6f4ea] to show through
      ctx.clearRect(0, 0, width, height);

      // Helper function for radial gradients
      const drawOrb = (x: number, y: number, radius: number, colorStop1: string, colorStop2: string) => {
        // Guard against negative radius
        if (radius <= 0) return;
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
        gradient.addColorStop(0, colorStop1);
        gradient.addColorStop(1, colorStop2);
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
      };

      // 2. "Darker and Bigger" at one end (Bottom Right)
      // Uses a Deep Emerald tone, anchored low and to the right.
      const x1 = width * 0.85 + Math.sin(time * 0.3) * 50;
      const y1 = height * 1.1; // Anchored slightly below screen
      const r1 = Math.max(width, height) * 0.75; // Large radius covers bottom right quadrant
      drawOrb(x1, y1, r1, 'rgba(6, 78, 59, 0.35)', 'rgba(6, 78, 59, 0)'); // emerald-900 at increased opacity for darker look

      // 3. "Lighter and Smaller" at the other end (Bottom Left)
      // Uses a brighter, minty Emerald tone.
      const x2 = width * 0.2 + Math.cos(time * 0.4) * 60;
      const y2 = height * 0.95;
      const r2 = Math.max(width, height) * 0.45; // Smaller radius
      drawOrb(x2, y2, r2, 'rgba(52, 211, 153, 0.18)', 'rgba(52, 211, 153, 0)'); // emerald-400

      // 4. Interactive "Spotlight" Orb (Follows mouse) - Subtle fill
      // Using a very light emerald/white mix to feel like a light source
      drawOrb(currentMouseX, currentMouseY, 300, 'rgba(167, 243, 208, 0.15)', 'rgba(167, 243, 208, 0)');

      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  const navigate = useNavigate();

  const scrapeWebsite = async (url: string) => {
    try {
      setIsScraping(true);
      const res = await fetch(`https://api.microlink.io/?url=${encodeURIComponent(url)}`);
      const data = await res.json();

      if (data.status === 'success') {
        const result = {
          title: data.data.title,
          description: data.data.description,
          image: data.data.image?.url,
          logo: data.data.logo?.url,
          url: data.data.url
        };

        console.log("Scraped Data:", result);
        setScrapedData(result);
        localStorage.setItem("scraped_data", JSON.stringify(result));

        // Auto-fill context if available and empty
        if (result.description && !formData.context) {
          setFormData(prev => ({ ...prev, context: result.description }));
        }
      }
    } catch (error) {
      console.error("Scraping failed:", error);
    } finally {
      setIsScraping(false);
    }
  };

  const handleNext = async () => {
    if (currentStep === 2 && formData.website) {
      await scrapeWebsite(formData.website);
    }

    if (currentStep < 4) {
      setCurrentStep(prev => prev + 1);
    } else {
      // Final step action (Finish/Continue)
      try {
        const userId = localStorage.getItem("user_id");
        if (userId) {
          const payload = new FormData();
          payload.append("user_id", userId);

          if (formData.logo) {
            payload.append("logo", formData.logo);
          }

          if (formData.assets && formData.assets.length > 0) {
            formData.assets.forEach(file => {
              payload.append("assets", file);
            });
          }

          // Send to backend - non-blocking for UI but we await to ensure it starts
          await fetch("http://localhost:8000/onboarding/", {
            method: "POST",
            body: payload
          });
        }
      } catch (error) {
        console.error("Failed to upload onboarding assets:", error);
      }

      onFinish(formData);
      navigate('/agent');
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleContextFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFormData({ ...formData, contextFile: e.target.files[0] });
    }
  };

  const removeContextFile = () => {
    setFormData({ ...formData, contextFile: null });
    if (contextFileRef.current) {
      contextFileRef.current.value = '';
    }
  };

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.type === 'image/png') {
        setFormData({ ...formData, logo: file });
      } else {
        alert('Please upload a PNG file for the logo.');
      }
    }
  };

  const handleAssetsUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFormData({ ...formData, assets: [...formData.assets, ...Array.from(e.target.files)] });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 font-sans relative overflow-hidden bg-[#e6f4ea]">

      {/* Interactive Canvas Background */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 z-0 pointer-events-none"
        style={{ width: '100%', height: '100%' }}
      />

      {/* Main Container Box - Reduced width to max-w-lg */}
      <div className="w-full max-w-lg bg-white rounded-3xl border border-emerald-500 shadow-2xl overflow-hidden flex flex-col min-h-[600px] relative animate-pop-in z-10">

        {/* Top Section: Progress Indicator */}
        <div className="pt-10 pb-8 px-12 bg-white/50 backdrop-blur-sm border-b border-gray-100/50">
          <div className="relative flex justify-between items-center w-full">

            {/* Connecting Line background */}
            <div className="absolute top-1/2 left-0 w-full h-0.5 bg-gray-100 -translate-y-1/2 z-0" />

            {/* Connecting Line active progress */}
            <div
              className="absolute top-1/2 left-0 h-0.5 bg-[#006838] -translate-y-1/2 z-0 transition-all duration-500 ease-in-out"
              style={{ width: `${((currentStep - 1) / (steps.length - 1)) * 100}%` }}
            />

            {/* Circles */}
            {steps.map((step) => (
              <div key={step.id} className="relative z-10 flex flex-col items-center gap-2">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${currentStep >= step.id
                    ? 'bg-[#006838] border-[#006838] text-white shadow-lg'
                    : 'bg-white border-gray-200 text-gray-300'
                    }`}
                >
                  {currentStep > step.id ? <Check size={18} /> : <span className="font-bold text-sm">{step.id}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Middle Section: Content */}
        <div className="flex-1 flex flex-col px-12 py-8 overflow-y-auto">

          {/* Step 1: Company Name */}
          {currentStep === 1 && (
            <div className="flex flex-col flex-1 justify-start pt-12 space-y-8 animate-pop-in">
              {/* Logo Insertion */}
              <div className="flex justify-center mb-6">
                <span className="text-5xl font-black tracking-tighter text-black">
                  PRISM <span className="text-emerald-600">MOTION</span>
                </span>
              </div>

              <div className="space-y-2 text-center mb-4">
                <h2 className="text-2xl font-bold text-gray-900">Welcome! Let's get started.</h2>
                <p className="text-gray-500">What is the name of your company?</p>
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-semibold text-gray-700">Company Name</label>
                <input
                  type="text"
                  value={formData.companyName}
                  onChange={(e) => setFormData({ ...formData, companyName: e.target.value })}
                  placeholder="e.g. Prism Pharma Innovations"
                  className="w-full px-5 py-4 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10 outline-none transition-all text-lg text-black"
                  autoFocus
                />
              </div>
            </div>
          )}

          {/* Step 2: Website & Email */}
          {currentStep === 2 && (
            <div className="flex flex-col flex-1 justify-center space-y-6 animate-pop-in">
              <div className="space-y-2 text-center mb-4">
                <h2 className="text-2xl font-bold text-gray-900">Where can we find you?</h2>
                <p className="text-gray-500">Provide your digital presence details.</p>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="block text-sm font-semibold text-gray-700 flex items-center gap-2">
                    <Globe size={16} /> Website URL
                  </label>
                  <input
                    type="url"
                    value={formData.website}
                    onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                    placeholder="https://example.com"
                    className="w-full px-5 py-4 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10 outline-none transition-all text-lg text-black"
                  />
                </div>

                <div className="space-y-2">
                  <label className="block text-sm font-semibold text-gray-700 flex items-center gap-2">
                    <Mail size={16} /> Company Email
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="contact@example.com"
                    className="w-full px-5 py-4 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10 outline-none transition-all text-lg text-black"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Company Context */}
          {currentStep === 3 && (
            <div className="flex flex-col flex-1 justify-center space-y-6 animate-pop-in">
              <div className="space-y-2 text-center mb-4">
                <h2 className="text-2xl font-bold text-gray-900">Tell us about your work.</h2>
                <p className="text-gray-500">Help our AI understand your products and audience.</p>
              </div>

              <div className="space-y-2 flex-1 flex flex-col relative">
                <label className="block text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <FileText size={16} /> Company Context
                </label>

                <div className="relative flex-1 flex flex-col">
                  <textarea
                    value={formData.context}
                    onChange={(e) => setFormData({ ...formData, context: e.target.value })}
                    placeholder="Describe what your company does, your products, and your target audience..."
                    className="w-full h-full flex-1 px-5 py-4 pb-14 rounded-xl border border-gray-200 bg-gray-50 focus:bg-white focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10 outline-none transition-all text-lg resize-none text-black"
                  />

                  {/* Floating Attach Section */}
                  <div className="absolute bottom-4 right-4 flex items-center gap-3">
                    <input
                      type="file"
                      ref={contextFileRef}
                      hidden
                      accept=".pdf,.doc,.docx,.txt"
                      onChange={handleContextFileChange}
                    />

                    {/* Selected File Chip */}
                    {formData.contextFile && (
                      <div className="flex items-center gap-2 bg-emerald-100 text-emerald-800 px-3 py-1.5 rounded-lg text-xs font-bold border border-emerald-200 shadow-sm animate-pop-in">
                        <span className="truncate max-w-[150px]">{formData.contextFile.name}</span>
                        <button
                          onClick={removeContextFile}
                          className="hover:text-emerald-950 p-0.5 rounded-full hover:bg-emerald-200/50 transition-colors"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    )}

                    {/* Attach Button (Icon Only) */}
                    <button
                      onClick={() => contextFileRef.current?.click()}
                      className="flex items-center justify-center text-gray-500 hover:text-emerald-600 transition-colors bg-white/80 hover:bg-white p-3 rounded-full border border-transparent hover:border-gray-200 shadow-sm"
                      title="Attach file (PDF, Word)"
                    >
                      <Paperclip size={20} />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Assets Upload */}
          {currentStep === 4 && (
            <div className="flex flex-col flex-1 space-y-6 animate-pop-in">
              <div className="space-y-2 text-center">
                <h2 className="text-2xl font-bold text-gray-900">Brand Assets</h2>
                <p className="text-gray-500">Upload your materials for video generation.</p>
              </div>

              <div className="flex flex-col space-y-6">
                {/* Logo Upload */}
                <div className="space-y-3">
                  <label className="block text-sm font-bold text-gray-900">Logo Upload <span className="text-emerald-500 text-xs font-normal ml-1">(PNG only)</span></label>
                  <div className="relative group">
                    <input
                      type="file"
                      accept="image/png"
                      onChange={handleLogoUpload}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                    />
                    <div className={`w-full h-32 border-2 border-dashed rounded-xl flex flex-col items-center justify-center transition-all ${formData.logo ? 'border-emerald-500 bg-emerald-50' : 'border-gray-200 hover:border-emerald-400 hover:bg-gray-50'}`}>
                      {formData.logo ? (
                        <div className="text-center p-4">
                          <div className="w-10 h-10 bg-white rounded-full shadow-sm mx-auto mb-2 flex items-center justify-center">
                            <Check className="text-emerald-600" size={20} />
                          </div>
                          <p className="text-emerald-700 font-bold">Logo uploaded successfully</p>
                          <p className="text-emerald-600/70 text-sm mt-1 max-w-[200px] truncate mx-auto">{formData.logo.name}</p>
                        </div>
                      ) : (
                        <div className="text-center p-4 text-gray-400">
                          <Upload className="mx-auto mb-2" />
                          <p className="text-sm font-medium text-gray-600">Drop PNG here</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Assets Upload */}
                <div className="space-y-3">
                  <label className="block text-sm font-bold text-gray-900">Image Assets <span className="text-gray-400 text-xs font-normal ml-1">(Multiple)</span></label>
                  <div className="relative group">
                    <input
                      type="file"
                      multiple
                      accept="image/*"
                      onChange={handleAssetsUpload}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20"
                    />
                    <div className={`w-full h-32 border-2 border-dashed border-gray-200 rounded-xl flex flex-col items-center justify-center transition-all ${formData.assets.length > 0 ? 'border-emerald-500 bg-emerald-50' : 'hover:border-emerald-400 hover:bg-gray-50'}`}>
                      {formData.assets.length > 0 ? (
                        <div className="text-center p-4">
                          <div className="w-10 h-10 bg-white rounded-full shadow-sm mx-auto mb-2 flex items-center justify-center">
                            <Check className="text-emerald-600" size={20} />
                          </div>
                          <p className="text-emerald-700 font-bold">Files uploaded successfully</p>
                          <p className="text-emerald-600/70 text-sm mt-1">{formData.assets.length} items added</p>
                        </div>
                      ) : (
                        <div className="text-center p-4 text-gray-400">
                          <Upload className="mx-auto mb-2" />
                          <p className="text-sm font-medium text-gray-600">Drop images here</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Bottom Section: Navigation */}
        <div className="py-6 px-12 bg-[#006838] border-t border-emerald-800 flex justify-between items-center">
          <button
            onClick={handlePrev}
            disabled={currentStep === 1}
            className={`flex items-center gap-2 text-sm font-bold transition-colors ${currentStep === 1
              ? 'text-white/30 cursor-not-allowed'
              : 'text-white hover:text-emerald-200'
              }`}
          >
            <ArrowLeft size={18} />
            Previous
          </button>

          <button
            onClick={handleNext}
            disabled={isScraping}
            className={`flex items-center gap-2 text-sm font-bold text-white hover:text-emerald-200 transition-colors ${isScraping ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {isScraping ? 'Analyzing...' : (currentStep === 4 ? 'Finish' : 'Next')}
            {!isScraping && currentStep !== 4 && <ArrowRight size={18} />}
          </button>
        </div>

        {/* Loading Overlay */}
        {isScraping && (
          <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-50 flex flex-col items-center justify-center animate-fade-in">
            <div className="w-12 h-12 border-4 border-gray-200 border-t-[#006838] rounded-full animate-spin mb-4"></div>
            <p className="text-[#006838] font-bold text-lg animate-pulse">Analyzing website...</p>
          </div>
        )}

      </div>
    </div>
  );
};

export default Onboarding;