import React from 'react';
import { ArrowRight, PlayCircle } from 'lucide-react';

interface HeroProps {
  onStart: () => void;
}

const Hero: React.FC<HeroProps> = ({ onStart }) => {
  const prismText = "PRISM";
  const motionText = "MOTION";

  // Create a strip of 5 'O's for the slot machine effect.
  // Fewer items allow for a slow movement speed within a short total duration.
  const slotStrip = Array(5).fill('O');

  return (
    <section className="relative w-full min-h-screen flex items-center justify-center overflow-hidden">

      {/* Background Layer */}
      <div
        className="absolute inset-0 z-0"
        style={{
          backgroundImage: `url(https://file-service.Mochi.co/image_0.png)`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      />

      {/* Gradient Overlay - Very Light Green Tint to match new background */}
      <div className="absolute inset-0 z-0 bg-[#f8fcf9]/70" />

      {/* Removed mt-24 to center the group vertically in the screen */}
      <div className="container mx-auto px-6 relative z-10 flex flex-col items-center text-center mt-20">

        {/* Centered Content */}
        <div className="flex flex-col items-center max-w-7xl">

          {/* Main Heading - Increased Size */}
          <h1 className="text-7xl md:text-9xl lg:text-[11rem] font-black text-black leading-[0.85] tracking-tighter relative flex flex-col items-center">

            {/* PRISM - Animate Entire Word at Once (Fade Pop) */}
            {/* Reduced margin-bottom to decrease space */}
            <span className="block mb-1 md:mb-0 animate-pop-in">
              {prismText}
            </span>

            {/* MOTION - Sequenced Animation */}
            {/* Changed margin-top to 0 and negative margin on desktop to pull closer to PRISM */}
            <span className="relative inline-flex items-baseline mt-0 md:-mt-3 lg:-mt-4">
              {motionText.split('').map((char, index) => {
                return (
                  <React.Fragment key={`motion-${index}`}>
                    {char === 'O' ? (
                      /* The Slot Machine 'O' */
                      <span
                        className="relative inline-flex justify-center overflow-hidden align-baseline h-[1.3em] w-[0.9em] mx-0 animate-pop-in text-emerald-500"
                        style={{ animationDelay: '0.8s' }}
                      >
                        {/* Phantom for width reference, hidden */}
                        <span className="opacity-0 select-none flex items-center">{char}</span>

                        {/* Animated Strip - Height 500% for 5 items */}
                        <span
                          className="absolute top-0 left-0 w-full h-[500%] flex flex-col animate-slot will-change-transform"
                          style={{ animationDelay: '0.8s' }}
                        >
                          {slotStrip.map((stripChar, i) => (
                            /* Each item is 1/5th = 20% height */
                            <span key={i} className="h-[20%] flex items-center justify-center">
                              {stripChar}
                            </span>
                          ))}
                        </span>
                      </span>
                    ) : (
                      /* Normal Character - M, T, I, N */
                      <span
                        className="inline-block animate-pop-in"
                        style={{ animationDelay: '0.8s' }}
                      >
                        {char}
                      </span>
                    )}
                  </React.Fragment>
                );
              })}

              {/* Underline Decoration 1 */}
              <svg className="absolute w-full h-4 md:h-6 -bottom-1 md:-bottom-2 left-6 md:left-10 text-emerald-500 animate-underline pointer-events-none" style={{ animationDelay: '3.0s' }} viewBox="0 0 200 9" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M2.00025 6.99997C2.00025 6.99997 113.375 8.12667 170.375 1.99999" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
              </svg>

              {/* Underline Decoration 2 */}
              <svg className="absolute w-full h-4 md:h-6 -bottom-5 md:-bottom-8 left-6 md:left-10 text-emerald-500 animate-underline pointer-events-none" style={{ animationDelay: '3.2s' }} viewBox="0 0 200 9" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M2.00025 6.99997C2.00025 6.99997 113.375 8.12667 170.375 1.99999" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
              </svg>
            </span>
          </h1>

          {/* Tagline */}
          <p className="text-lg md:text-xl text-gray-800 max-w-4xl font-medium animate-pop-in mt-10 md:mt-16" style={{ animationDelay: '1.2s' }}>
            Weeks of pharma video work - done in minutes.
          </p>

          {/* Single Button */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-8 md:pt-10">
            <button
              onClick={onStart}
              className="flex items-center justify-center bg-black text-white px-12 py-5 rounded-full text-lg font-bold hover:bg-emerald-500 hover:text-black transition-colors duration-300 shadow-xl animate-pop-in"
              style={{ animationDelay: '1.4s' }}
            >
              <span>Insight Motion</span>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;