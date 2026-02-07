import React, { useRef, useEffect, useState } from 'react';

const projects = [
  {
    id: 1,
    src: "/video1.mp4",
    title: "Featured Project 1"
  },
  {
    id: 2,
    src: "/video2.mp4",
    title: "Featured Project 2"
  },
  {
    id: 3,
    src: "/video1.mp4",
    title: "Featured Project 3"
  },
];

const FeaturedProjects: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [progress, setProgress] = useState(0);

  // Handle scroll to drive animation
  useEffect(() => {
    const handleScroll = () => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const viewHeight = window.innerHeight;

      // Effective scroll distance (Total height - 1 Viewport)
      const scrollDist = rect.height - viewHeight;
      if (scrollDist <= 0) return;

      // Normalized scroll progress (0 to 1)
      const rawP = -rect.top / scrollDist;
      const p = Math.max(0, Math.min(1, rawP));

      // Map 0..1 to 0..2 (Linear flow: Index 0 -> 1 -> 2)
      // Stops at the last item (2) instead of cycling back to 0 (3)
      setProgress(p * 2);
    };

    window.addEventListener('scroll', handleScroll);
    handleScroll(); // Initial check
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Calculate transforms for 3D Carousel effect
  const getCardStyle = (index: number) => {
    // Circular carousel logic
    // Angle offset: Spread items by 120deg (2PI/3)
    // Progress shifts the entire carousel rotation
    const angleOffset = (index - progress) * (2 * Math.PI / 3);

    // Layout Calculation
    // X: Horizontal position (sin)
    // Z: Depth (cos)
    const radiusX = 40; // 40vw spread
    const x = Math.sin(angleOffset) * radiusX;

    // Z-depth determines scale and stacking order
    // cos goes from 1 (front) to -0.5 (back left/right)
    const zBase = Math.cos(angleOffset);

    // Scale: Front(1) -> Back(0.3)
    // Adjusted range: 0.3 to 1.0 for smaller side items
    const scale = 0.3 + ((zBase + 0.5) / 1.5) * 0.7;

    // Opacity & Emphasis
    // Front(1) -> Back(0.6)
    const opacity = 0.6 + ((zBase + 0.5) / 1.5) * 0.4;

    // Z-Index: Front items cover back items
    const zIndex = Math.round(zBase * 100);

    return {
      transform: `translateX(${x}vw) scale(${scale})`,
      zIndex: zIndex + 100, // Ensure positive context
      opacity: opacity,
      filter: zBase > 0.8 ? 'none' : 'grayscale(30%) brightness(0.7)', // Visual hierarchy
    };
  };

  return (
    // Tall container for scroll space
    // Adjusted height to 300vh since we only have 2 transitions (0->1->2)
    <section ref={containerRef} className="relative h-[300vh] bg-[#f8fcf9]" id="projects">
      {/* Sticky viewport */}
      <div className="sticky top-0 h-screen w-full flex flex-col items-center justify-center overflow-hidden perspective-1000">

        {/* Section Title - Updated styling for single line */}
        <div className="absolute top-12 md:top-20 z-50 text-center w-full px-4">
          <h2 className="font-black tracking-tighter mb-0 uppercase leading-[0.9] flex flex-wrap justify-center gap-2 md:gap-6">
            <span className="text-emerald-500 text-5xl md:text-[6vw]">Featured</span>
            <span className="text-black text-5xl md:text-[6vw]">Projects</span>
          </h2>
        </div>

        {/* Carousel Container - Added pt-32 for spacing from title */}
        <div className="relative w-full h-full flex items-center justify-center pointer-events-none pt-32 md:pt-40">
          {projects.map((item, i) => (
            <div
              key={item.id}
              className="absolute w-[70vw] md:w-[50vw] aspect-video bg-gray-900 rounded-xl shadow-2xl overflow-hidden will-change-transform transition-transform duration-75 ease-linear"
              style={getCardStyle(i)}
            >
              <video
                src={item.src}
                autoPlay
                loop
                muted
                playsInline
                className="w-full h-full object-cover"
              />

              {/* Overlay Content (Optional) */}
              <div className="absolute inset-0 bg-black/10" />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default FeaturedProjects;