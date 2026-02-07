import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
  Easing,
} from "remotion";
import { useState } from "react";

const FadeInUp: React.FC<{ children: React.ReactNode; delay?: number }> = ({ 
  children, 
  delay = 0 
}) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(
    frame,
    [delay, delay + 30],
    [0, 1],
    {
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.ease),
    }
  );

  const translateY = interpolate(
    frame,
    [delay, delay + 30],
    [50, 0],
    {
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.back(1.5)),
    }
  );

  const scale = interpolate(
    frame,
    [delay, delay + 30],
    [0.95, 1],
    {
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.ease),
    }
  );

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${translateY}px) scale(${scale})`,
      }}
    >
      {children}
    </div>
  );
};

const KenBurnsImage: React.FC<{ src: string }> = ({ src }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const [error, setError] = useState(false);

  // More dramatic zoom with smooth easing
  const scale = interpolate(
    frame,
    [0, durationInFrames],
    [1.0, 1.15],
    {
      easing: Easing.inOut(Easing.ease),
    }
  );

  // Subtle pan effect
  const translateX = interpolate(
    frame,
    [0, durationInFrames],
    [-2, 2],
    {
      easing: Easing.inOut(Easing.ease),
    }
  );

  const getImageSrc = (path: string): string => {
    if (!path) return "";
    if (path.startsWith("http://") || path.startsWith("https://")) {
      return path;
    }
    if (path.startsWith("/")) {
      return `file://${path}`;
    }
    return staticFile(path);
  };

  if (error || !src) {
    return (
      <div
        style={{
          position: "absolute",
          width: "100%",
          height: "100%",
          background: "linear-gradient(135deg, #1e1e2e 0%, #2d2d3d 100%)",
        }}
      />
    );
  }

  return (
    <Img
      src={getImageSrc(src)}
      onError={() => {
        console.error(`Failed to load image: ${src}`);
        setError(true);
      }}
      style={{
        position: "absolute",
        width: "100%",
        height: "100%",
        objectFit: "cover",
        transform: `scale(${scale}) translateX(${translateX}%)`,
        filter: "brightness(0.75) contrast(1.1)",
      }}
    />
  );
};

// Animated particles overlay
const ParticlesOverlay: React.FC = () => {
  const frame = useCurrentFrame();
  
  const particles = Array.from({ length: 20 }, (_, i) => {
    const x = (i * 37) % 100;
    const baseY = (i * 23) % 100;
    const speed = 0.5 + (i % 3) * 0.3;
    const y = (baseY + (frame * speed) / 10) % 120 - 10;
    const opacity = 0.1 + ((i % 5) / 10);
    const size = 2 + (i % 4);
    
    return { x, y, opacity, size };
  });

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {particles.map((p, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.size,
            borderRadius: "50%",
            backgroundColor: "white",
            opacity: p.opacity,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};

// Word-by-word animation
const AnimatedText: React.FC<{ text: string; delay?: number }> = ({ 
  text, 
  delay = 0 
}) => {
  const frame = useCurrentFrame();
  const words = text.split(" ");
  
  return (
    <div style={{ fontSize: 42, lineHeight: 1.4, textAlign: "center" }}>
      {words.map((word, i) => {
        const wordDelay = delay + i * 3;
        const opacity = interpolate(
          frame,
          [wordDelay, wordDelay + 8],
          [0, 1],
          { extrapolateRight: "clamp" }
        );
        
        const translateY = interpolate(
          frame,
          [wordDelay, wordDelay + 8],
          [10, 0],
          {
            extrapolateRight: "clamp",
            easing: Easing.out(Easing.ease),
          }
        );
        
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              opacity,
              transform: `translateY(${translateY}px)`,
              marginRight: "0.3em",
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
};

// Progress bar at bottom
const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  
  const progress = (frame / durationInFrames) * 100;
  
  return (
    <div
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        height: 4,
        background: "rgba(255,255,255,0.1)",
      }}
    >
      <div
        style={{
          height: "100%",
          width: `${progress}%`,
          background: "linear-gradient(90deg, #4f46e5, #06b6d4)",
        }}
      />
    </div>
  );
};

// Scene number indicator
const SceneIndicator: React.FC<{ sceneNumber: number; totalScenes: number }> = ({
  sceneNumber,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  
  const opacity = interpolate(frame, [0, 20, 280, 300], [0, 1, 1, 0], {
    extrapolateRight: "clamp",
  });
  
  return (
    <div
      style={{
        position: "absolute",
        top: 60,
        right: 80,
        opacity,
        fontSize: 18,
        fontWeight: 600,
        color: "rgba(255,255,255,0.6)",
        letterSpacing: 2,
      }}
    >
      {sceneNumber} / {totalScenes}
    </div>
  );
};

// Glowing accent line
const AccentLine: React.FC = () => {
  const frame = useCurrentFrame();
  
  const width = interpolate(frame, [10, 40], [0, 200], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });
  
  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -200px)",
        width,
        height: 3,
        background: "linear-gradient(90deg, transparent, #06b6d4, transparent)",
        boxShadow: "0 0 20px #06b6d4",
      }}
    />
  );
};

export const ComplianceVideo: React.FC<{ scenes: any[] }> = ({ scenes }) => {
  const { fps } = useVideoConfig();
  let currentFrame = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0e0e11", color: "white" }}>
      {scenes.map((scene, sceneIndex) => {
        const duration = scene.duration_sec * fps;
        const start = currentFrame;
        currentFrame += duration;

        return (
          <Sequence key={scene.scene_id} from={start} durationInFrames={duration}>
            <AbsoluteFill>
              {/* Background image with Ken Burns */}
              {scene.image?.src && <KenBurnsImage src={scene.image.src} />}

              {/* Animated particles */}
              <ParticlesOverlay />

              {/* Scene indicator */}
              <SceneIndicator 
                sceneNumber={sceneIndex + 1} 
                totalScenes={scenes.length} 
              />
              
              {/* Accent line */}
              <AccentLine />

              {/* Dark overlay with vignette */}
              <AbsoluteFill
                style={{
                  background:
                    "radial-gradient(ellipse at center, rgba(0,0,0,0.4) 0%, rgba(0,0,0,0.85) 100%)",
                  justifyContent: "center",
                  alignItems: "center",
                  padding: 120,
                }}
              >
                <FadeInUp delay={10}>
                  <div
                    style={{
                      maxWidth: 1100,
                      fontWeight: 500,
                      letterSpacing: 0.3,
                      textShadow: "2px 2px 20px rgba(0,0,0,0.8)",
                    }}
                  >
                    <AnimatedText text={scene.script} delay={15} />
                  </div>
                </FadeInUp>
              </AbsoluteFill>

              {/* Progress bar */}
              <ProgressBar />

              {scene.audio_src && <Audio src={scene.audio_src} />}
            </AbsoluteFill>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};