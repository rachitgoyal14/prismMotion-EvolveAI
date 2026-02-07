import React, { useEffect, useRef, useState } from "react";
import Matter from "matter-js";

/* -----------------------------
   PHYSICS PILLS COMPONENT
------------------------------ */
const PhysicsPills = () => {
  const sceneRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<Matter.Engine | null>(null);
  const runnerRef = useRef<Matter.Runner | null>(null);
  
  // State to store physics body positions for rendering HTML overlay
  const [bodies, setBodies] = useState<any[]>([]);
  const [inView, setInView] = useState(false);

  const pillsData = [
    { id: 1, text: "Social Media Engagement Videos", sub: "Video Service", width: 340 },
    { id: 2, text: "Informative Medical Videos", sub: "Video Service", width: 300 },
    { id: 3, text: "Brand Promotion Videos", sub: "Video Service", width: 280 },
    { id: 4, text: "Product Advertisement Videos", sub: "Video Service", width: 320 },
    { id: 5, text: "Disease Awareness Campaigns", sub: "Video Service", width: 330 },
    { id: 6, text: "Patient Education Videos", sub: "Video Service", width: 290 },
    { id: 7, text: "Regulatory & Compliance Videos", sub: "Video Service", width: 340 },
    { id: 8, text: "Safety Communication Videos", sub: "Video Service", width: 320 },
    { id: 9, text: "Doctor / HCP Engagement Videos", sub: "Video Service", width: 350 },
    { id: 10, text: "Instagram Reels & YouTube Shorts", sub: "Video Service", width: 360 },
    { id: 11, text: "Training & Internal Communication Videos", sub: "Video Service", width: 420 },
  ];

  // Intersection Observer to trigger physics only when visible
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
        }
      },
      { threshold: 0.01 } // Trigger almost immediately when in view
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, []);

  // Initialize Matter.js
  useEffect(() => {
    if (!inView || !sceneRef.current || !containerRef.current) return;
    if (engineRef.current) return; // Already initialized

    // Setup basic Engine
    const Engine = Matter.Engine,
          Render = Matter.Render,
          Runner = Matter.Runner,
          Bodies = Matter.Bodies,
          Composite = Matter.Composite,
          Mouse = Matter.Mouse,
          MouseConstraint = Matter.MouseConstraint;

    const engine = Engine.create();
    const world = engine.world;
    engineRef.current = engine;

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;

    // Create Renderer (Invisible, just for mouse interaction reference if needed, 
    // but we primarily need the canvas for MouseConstraint)
    const render = Render.create({
      element: sceneRef.current,
      engine: engine,
      options: {
        width,
        height,
        background: 'transparent',
        wireframes: false, // We won't actually see this because we'll render HTML on top, but useful for debug
        showAngleIndicator: false
      }
    });

    // Make the canvas completely transparent as we use HTML for visuals
    render.canvas.style.opacity = '0';
    render.canvas.style.position = 'absolute';
    render.canvas.style.top = '0';
    render.canvas.style.left = '0';
    render.canvas.style.pointerEvents = 'auto'; // allow mouse interaction on canvas

    // Boundaries
    const ground = Bodies.rectangle(width / 2, height + 30, width, 60, { 
      isStatic: true,
      render: { visible: false } 
    });
    const leftWall = Bodies.rectangle(-30, height / 2, 60, height * 2, { 
      isStatic: true,
      render: { visible: false } 
    });
    const rightWall = Bodies.rectangle(width + 30, height / 2, 60, height * 2, { 
      isStatic: true,
      render: { visible: false } 
    });
    
    // Top wall (Ceiling) - initially separate, added after delay
    const topWall = Bodies.rectangle(width / 2, -30, width, 60, { 
      isStatic: true,
      render: { visible: false } 
    });

    Composite.add(world, [ground, leftWall, rightWall]);

    // Create Pill Bodies
    const pillBodies = pillsData.map((pill, index) => {
      // Random starting positions above the view
      const x = Math.random() * (width - 100) + 50;
      // Stagger start height more to accommodate more pills without immediate collision overlapping too much
      const y = -Math.random() * 800 - 100; 
      
      const body = Bodies.rectangle(x, y, pill.width, 80, {
        chamfer: { radius: 40 }, // Pill shape in physics
        restitution: 0.5, // Bounciness
        friction: 0.5,
        angle: (Math.random() - 0.5) * 0.5, // Random slight rotation
        render: { visible: false } // Hidden in canvas, rendered via HTML
      });
      // Attach data for React mapping
      (body as any).pillData = pill;
      return body;
    });

    Composite.add(world, pillBodies);

    // Add top barrier after pills have likely fallen (2.5 seconds)
    // This prevents them from being dragged out of the top view
    const topWallTimer = setTimeout(() => {
      Composite.add(world, topWall);
    }, 2500);

    // Mouse Interaction
    const mouse = Mouse.create(render.canvas);
    const mouseConstraint = MouseConstraint.create(engine, {
      mouse: mouse,
      constraint: {
        stiffness: 0.2,
        render: {
          visible: false
        }
      }
    });

    // Important: keep mouse scroll working
    mouseConstraint.mouse.element.removeEventListener("mousewheel", (mouseConstraint.mouse as any).mousewheel);
    mouseConstraint.mouse.element.removeEventListener("DOMMouseScroll", (mouseConstraint.mouse as any).mousewheel);

    Composite.add(world, mouseConstraint);

    // Run the engine
    Render.run(render);
    const runner = Runner.create();
    runnerRef.current = runner;
    Runner.run(runner, engine);

    // Render Loop for HTML syncing
    let animationFrameId: number;
    const updateHTML = () => {
      const updatedBodies = pillBodies.map(body => ({
        id: (body as any).pillData.id,
        x: body.position.x,
        y: body.position.y,
        angle: body.angle,
        width: (body as any).pillData.width,
        data: (body as any).pillData
      }));
      setBodies(updatedBodies);
      animationFrameId = requestAnimationFrame(updateHTML);
    };
    updateHTML();

    // Cleanup
    return () => {
      clearTimeout(topWallTimer);
      Render.stop(render);
      Runner.stop(runner);
      cancelAnimationFrame(animationFrameId);
      if (render.canvas) render.canvas.remove();
      Composite.clear(world, false);
      Engine.clear(engine);
    };
  }, [inView]);

  return (
    <div ref={containerRef} className="relative w-full h-[400px] bg-transparent mt-8 overflow-hidden">
      {/* Physics Debug/Interaction Layer */}
      <div ref={sceneRef} className="absolute inset-0 z-20" />

      {/* HTML Overlay Layer */}
      <div className="absolute inset-0 z-10 pointer-events-none">
        {bodies.map((body) => (
          <div
            key={body.id}
            className="absolute flex flex-col justify-center items-start px-8 rounded-full overflow-hidden"
            style={{
              width: `${body.width}px`,
              height: '80px',
              backgroundColor: '#006838', // Footer Color
              transform: `translate(${body.x - body.width / 2}px, ${body.y - 40}px) rotate(${body.angle}rad)`,
              transformOrigin: '50% 50%',
              willChange: 'transform',
            }}
          >
            <span className="text-[10px] uppercase tracking-wider text-white/60 mb-0.5 font-bold">
              {body.data.sub}
            </span>
            <span className="text-sm md:text-base font-bold text-white leading-tight overflow-hidden text-ellipsis w-full">
              {body.data.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

/* -----------------------------
   SECTION HEADER
------------------------------ */
const SectionHeader = () => {
  return (
    <div className="flex flex-col items-center mb-8">
      {/* Increased height to prevent cropping of descenders */}
      <div className="relative w-full h-[12vw] md:h-[10vw] flex items-end justify-center">
        <h2 className="w-full text-center z-10 leading-[0.94]">
          <span className="inline-block text-[6vw] md:text-[5vw] font-black tracking-[-0.2vw] text-black whitespace-nowrap uppercase">
            <span className="text-emerald-500">Why</span> Prism Motion?
          </span>
        </h2>
      </div>
      
      {/* Physics Pills Interaction Area */}
      <PhysicsPills />

      <p className="text-gray-600 max-w-3xl mx-auto mt-12 text-center text-lg md:text-2xl font-medium leading-relaxed">
        We transform complex medical information into engaging, compliant video experiences powered by AI.
      </p>
    </div>
  );
};

/* -----------------------------
   MAIN FEATURES SECTION
------------------------------ */
const Features: React.FC = () => {
  return (
    // Removed -mt-20 and added pt-0 to maintain natural spacing
    <section id="technology" className="pt-0 pb-24 bg-transparent relative z-20 overflow-hidden">
      <div className="container mx-auto px-6">
        <SectionHeader />
      </div>
    </section>
  );
};

export default Features;