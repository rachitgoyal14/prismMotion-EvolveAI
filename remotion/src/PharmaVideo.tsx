import React from "react";
import {
  AbsoluteFill,
  Sequence,
  Img,
  useVideoConfig,
  OffthreadVideo,
  Audio,
  staticFile,
  useCurrentFrame,
  interpolate,
  Easing,
} from "remotion";

export type AnimationConfig = {
  /* Entrance animation */
  entrance?: {
    type: "fade" | "slideIn" | "zoomIn" | "slideUp" | "slideDown" | "slideLeft" | "slideRight";
    duration_sec?: number;
    easing?: "linear" | "easeInOut" | "easeIn" | "easeOut";
  };
  /* Exit animation */
  exit?: {
    type: "fade" | "slideOut" | "zoomOut" | "slideUp" | "slideDown" | "slideLeft" | "slideRight";
    duration_sec?: number;
    easing?: "linear" | "easeInOut" | "easeIn" | "easeOut";
  };
  /* Transition to next scene */
  transition?: {
    type: "fade" | "slideLeft" | "slideRight" | "slideUp" | "slideDown" | "zoomFade";
    duration_sec?: number;
    easing?: "linear" | "easeInOut" | "easeIn" | "easeOut";
  };
};

export type Scene = {
  scene_id: number;
  duration_sec: number;
  concept: string;
  script: string;
  image?: { src: string; alt?: string };
  video?: { src: string } | null;
  /**
   * Audio path relative to Remotion public folder.
   * Example: "audio/<video_id>/scene_1.wav"
   */
  audio_src?: string | null;
  /** Animation configuration for this scene */
  animation?: AnimationConfig;
};

export type PharmaVideoProps = {
  scenes: Scene[];
  branding?: BrandingAssets;
};

/* ------------------ Metadata (SINGLE source of truth) ------------------ */
export const calculateMetadata = ({ props }: { props: PharmaVideoProps }) => {
  const fps = 30;

  const sceneFrames = props.scenes.reduce(
    (sum, s) => sum + Math.max(1, Math.ceil(s.duration_sec * fps)),
    0
  );

  const creditFrames = fps * 3;

  return {
    fps,
    width: 1920,
    height: 1080,
    durationInFrames: sceneFrames + creditFrames,
  };
};

/* ------------------ Branding Types ------------------ */
export type BrandingAssets = {
  logos?: string[];
  images?: string[];
};

/* ------------------ Helper to determine if path is local or remote ------------------ */
const isLocalPath = (src: string): boolean => {
  return !src.startsWith("http://") && !src.startsWith("https://");
};

/* Helper: get easing function */
const getEasingFunction = (easing?: string) => {
  switch (easing) {
    case "easeIn":
      return Easing.in(Easing.cubic);
    case "easeOut":
      return Easing.out(Easing.cubic);
    case "easeInOut":
      return Easing.inOut(Easing.cubic);
    case "linear":
    default:
      return Easing.linear;
  }
};

/* Helper: apply entrance animation to style */
const getEntranceStyle = (
  frame: number,
  entranceDuration: number,
  animationType: string
) => {
  const progress = Math.min(frame / entranceDuration, 1);
  const easing = getEasingFunction("easeOut");
  const easeProgress = easing(progress);

  const baseStyle: React.CSSProperties = {
    width: "100%",
    height: "100%",
    objectFit: "cover",
  };

  switch (animationType) {
    case "fade":
      return { ...baseStyle, opacity: easeProgress };
    case "slideIn":
    case "slideRight":
      return {
        ...baseStyle,
        opacity: easeProgress,
        transform: `translateX(${interpolate(progress, [0, 1], [100, 0])}%)`,
      };
    case "slideLeft":
      return {
        ...baseStyle,
        opacity: easeProgress,
        transform: `translateX(${interpolate(progress, [0, 1], [-100, 0])}%)`,
      };
    case "slideUp":
      return {
        ...baseStyle,
        opacity: easeProgress,
        transform: `translateY(${interpolate(progress, [0, 1], [100, 0])}%)`,
      };
    case "slideDown":
      return {
        ...baseStyle,
        opacity: easeProgress,
        transform: `translateY(${interpolate(progress, [0, 1], [-100, 0])}%)`,
      };
    case "zoomIn":
      return {
        ...baseStyle,
        opacity: easeProgress,
        transform: `scale(${interpolate(progress, [0, 1], [0.8, 1])})`,
      };
    default:
      return baseStyle;
  }
};

/* Helper: apply exit animation to style */
const getExitStyle = (
  frame: number,
  totalFrames: number,
  exitDuration: number,
  animationType: string
) => {
  const framesFromEnd = totalFrames - frame;
  const progress = Math.min(framesFromEnd / exitDuration, 1);
  const easing = getEasingFunction("easeIn");
  const easeProgress = easing(progress);

  const baseStyle: React.CSSProperties = {
    width: "100%",
    height: "100%",
    objectFit: "cover",
  };

  switch (animationType) {
    case "fade":
      return { ...baseStyle, opacity: easeProgress };
    case "slideOut":
    case "slideRight":
      return {
        ...baseStyle,
        opacity: easeProgress,
        transform: `translateX(${interpolate(progress, [0, 1], [0, 100])}%)`,
      };
    case "slideLeft":
      return {
        ...baseStyle,
        opacity: easeProgress,
        transform: `translateX(${interpolate(progress, [0, 1], [0, -100])}%)`,
      };
    case "slideUp":
      return {
        ...baseStyle,
        opacity: easeProgress,
        transform: `translateY(${interpolate(progress, [0, 1], [0, -100])}%)`,
      };
    case "slideDown":
      return {
        ...baseStyle,
        opacity: easeProgress,
        transform: `translateY(${interpolate(progress, [0, 1], [0, 100])}%)`,
      };
    case "zoomOut":
      return {
        ...baseStyle,
        opacity: easeProgress,
        transform: `scale(${interpolate(progress, [0, 1], [1, 0.8])})`,
      };
    default:
      return baseStyle;
  }
};

/* ========================================================================
   Reusable Sub-Components
   ======================================================================== */

/** Animated scene counter badge */
const SceneCounter: React.FC<{
  sceneIndex: number;
  totalScenes: number;
}> = ({ sceneIndex, totalScenes }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        top: 48,
        left: 56,
        opacity,
        display: "flex",
        alignItems: "center",
        gap: 10,
        zIndex: 100,
      }}
    >
      <div
        style={{
          background: "rgba(255,255,255,0.15)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          borderRadius: 40,
          padding: "10px 22px",
          display: "flex",
          alignItems: "center",
          gap: 8,
          border: "1px solid rgba(255,255,255,0.12)",
        }}
      >
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            backgroundColor: "#4ADE80",
            boxShadow: "0 0 8px rgba(74,222,128,0.6)",
          }}
        />
        <span
          style={{
            color: "rgba(255,255,255,0.95)",
            fontSize: 16,
            fontFamily:
              "'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif",
            fontWeight: 500,
            letterSpacing: "0.04em",
          }}
        >
          {String(sceneIndex + 1).padStart(2, "0")} / {String(totalScenes).padStart(2, "0")}
        </span>
      </div>
    </div>
  );
};

/** Animated progress bar at top of scene */
const SceneProgressBar: React.FC<{ durationFrames: number }> = ({
  durationFrames,
}) => {
  const frame = useCurrentFrame();
  const progress = Math.min(frame / durationFrames, 1);

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: 3,
        backgroundColor: "rgba(255,255,255,0.08)",
        zIndex: 200,
      }}
    >
      <div
        style={{
          width: `${progress * 100}%`,
          height: "100%",
          background: "linear-gradient(90deg, #4ADE80, #22D3EE)",
          borderRadius: "0 2px 2px 0",
          boxShadow: "0 0 12px rgba(74,222,128,0.4)",
        }}
      />
    </div>
  );
};

/** Animated subtitle/script overlay with word-by-word reveal */
const ScriptOverlay: React.FC<{
  script: string;
  durationFrames: number;
}> = ({ script, durationFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  /* Container fade in */
  const containerOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });
  /* Container slide up */
  const containerY = interpolate(frame, [0, 25], [30, 0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  /* Word-by-word reveal */
  const words = script.split(" ");
  const revealDuration = Math.min(durationFrames * 0.6, fps * 3);
  const framesPerWord = revealDuration / Math.max(words.length, 1);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "flex-start",
        padding: "0 56px 64px 56px",
        zIndex: 50,
        pointerEvents: "none",
      }}
    >
      {/* Multi-layer gradient for depth */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "55%",
          background: `
            linear-gradient(
              to top,
              rgba(0,0,0,0.88) 0%,
              rgba(0,0,0,0.7) 30%,
              rgba(0,0,0,0.35) 60%,
              rgba(0,0,0,0.08) 80%,
              transparent 100%
            )
          `,
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "relative",
          opacity: containerOpacity,
          transform: `translateY(${containerY}px)`,
          maxWidth: 1000,
        }}
      >
        {/* Subtle accent line */}
        <div
          style={{
            width: 48,
            height: 3,
            borderRadius: 2,
            background: "linear-gradient(90deg, #4ADE80, #22D3EE)",
            marginBottom: 18,
            opacity: interpolate(frame, [8, 25], [0, 0.9], {
              extrapolateRight: "clamp",
            }),
          }}
        />
        <p
          style={{
            margin: 0,
            fontFamily:
              "'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif",
            fontSize: 36,
            fontWeight: 500,
            lineHeight: 1.5,
            color: "white",
            textShadow: "0 2px 20px rgba(0,0,0,0.5)",
            letterSpacing: "-0.01em",
          }}
        >
          {words.map((word, i) => {
            const wordStart = i * framesPerWord;
            const wordOpacity = interpolate(
              frame,
              [wordStart, wordStart + 10],
              [0.2, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            return (
              <span
                key={`${word}-${i}`}
                style={{
                  opacity: wordOpacity,
                  transition: "opacity 0.1s",
                }}
              >
                {word}{" "}
              </span>
            );
          })}
        </p>
      </div>
    </AbsoluteFill>
  );
};

/** Subtle Ken Burns effect for images */
const KenBurnsWrapper: React.FC<{
  children: React.ReactNode;
  durationFrames: number;
}> = ({ children, durationFrames }) => {
  const frame = useCurrentFrame();

  const scale = interpolate(frame, [0, durationFrames], [1.0, 1.08], {
    extrapolateRight: "clamp",
    easing: Easing.linear,
  });
  const translateX = interpolate(frame, [0, durationFrames], [0, -1.2], {
    extrapolateRight: "clamp",
  });
  const translateY = interpolate(frame, [0, durationFrames], [0, -0.8], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        overflow: "hidden",
        position: "relative",
      }}
    >
      <div
        style={{
          width: "100%",
          height: "100%",
          transform: `scale(${scale}) translate(${translateX}%, ${translateY}%)`,
          transformOrigin: "center center",
        }}
      >
        {children}
      </div>
    </div>
  );
};

/* ========================================================================
   Scene visual with animation support (enhanced)
   ======================================================================== */
const SceneVisual: React.FC<{
  scene: Scene;
  durationFrames: number;
  logoSrc?: string | null;
  sceneIndex: number;
  totalScenes: number;
}> = ({ scene, durationFrames, logoSrc, sceneIndex, totalScenes }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const animConfig = scene.animation;
  const entranceDuration = (animConfig?.entrance?.duration_sec ?? 0.5) * fps;
  const exitDuration = (animConfig?.exit?.duration_sec ?? 0.5) * fps;

  let mediaStyle: React.CSSProperties = {
    width: "100%",
    height: "100%",
    objectFit: "cover",
  };

  // Apply entrance animation
  if (entranceDuration > 0 && animConfig?.entrance) {
    mediaStyle = getEntranceStyle(
      frame,
      entranceDuration,
      animConfig.entrance.type
    );
  }

  // Apply exit animation (only in last exitDuration frames)
  if (
    exitDuration > 0 &&
    animConfig?.exit &&
    frame > durationFrames - exitDuration
  ) {
    mediaStyle = getExitStyle(
      frame,
      durationFrames,
      exitDuration,
      animConfig.exit.type
    );
  }

  const isImage = !scene.video?.src && !!scene.image?.src;

  return (
    <AbsoluteFill style={{ backgroundColor: "#050505" }}>
      {/* Scene progress bar */}
      <SceneProgressBar durationFrames={durationFrames} />

      {/* Audio */}
      {scene.audio_src && <Audio src={staticFile(scene.audio_src)} />}

      {/* Media layer */}
      {scene.video?.src ? (
        <OffthreadVideo
          src={
            isLocalPath(scene.video.src)
              ? staticFile(scene.video.src)
              : scene.video.src
          }
          style={mediaStyle}
        />
      ) : scene.image?.src ? (
        <KenBurnsWrapper durationFrames={durationFrames}>
          <Img
            src={
              isLocalPath(scene.image.src)
                ? staticFile(scene.image.src)
                : scene.image.src
            }
            alt={scene.image.alt ?? ""}
            style={mediaStyle}
          />
        </KenBurnsWrapper>
      ) : (
        /* Missing media placeholder */
        <AbsoluteFill
          style={{
            justifyContent: "center",
            alignItems: "center",
            background:
              "radial-gradient(ellipse at center, #1a1a2e 0%, #0a0a0a 100%)",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 16,
            }}
          >
            <div
              style={{
                width: 72,
                height: 72,
                borderRadius: "50%",
                border: "2px solid rgba(255,255,255,0.1)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="rgba(255,255,255,0.3)"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <polyline points="21 15 16 10 5 21" />
              </svg>
            </div>
            <span
              style={{
                color: "rgba(255,255,255,0.3)",
                fontSize: 16,
                fontFamily:
                  "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
                fontWeight: 400,
                letterSpacing: "0.03em",
              }}
            >
              Media unavailable
            </span>
          </div>
        </AbsoluteFill>
      )}

      {/* Scene counter */}
      <SceneCounter sceneIndex={sceneIndex} totalScenes={totalScenes} />

      {/* Script overlay */}
      {scene.script && (
        <ScriptOverlay script={scene.script} durationFrames={durationFrames} />
      )}
    </AbsoluteFill>
  );
};

/* ========================================================================
   Transition overlay between scenes (enhanced)
   ======================================================================== */
const TransitionOverlay: React.FC<{
  from: number;
  transitionDuration: number;
  transitionType: string;
}> = ({ from, transitionDuration, transitionType }) => {
  const frame = useCurrentFrame();

  if (frame < from || frame >= from + transitionDuration) {
    return null;
  }

  const progress = (frame - from) / transitionDuration;
  const easing = getEasingFunction("easeInOut");
  const easeProgress = easing(progress);

  let overlayStyle: React.CSSProperties = {
    position: "absolute",
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    zIndex: 300,
  };

  switch (transitionType) {
    case "fade":
      overlayStyle.backgroundColor = `rgba(5, 5, 5, ${easeProgress})`;
      break;
    case "slideLeft":
      overlayStyle.backgroundColor = "#050505";
      overlayStyle.transform = `translateX(${interpolate(
        progress,
        [0, 1],
        [100, 0]
      )}%)`;
      break;
    case "slideRight":
      overlayStyle.backgroundColor = "#050505";
      overlayStyle.transform = `translateX(${interpolate(
        progress,
        [0, 1],
        [-100, 0]
      )}%)`;
      break;
    case "slideUp":
      overlayStyle.backgroundColor = "#050505";
      overlayStyle.transform = `translateY(${interpolate(
        progress,
        [0, 1],
        [100, 0]
      )}%)`;
      break;
    case "slideDown":
      overlayStyle.backgroundColor = "#050505";
      overlayStyle.transform = `translateY(${interpolate(
        progress,
        [0, 1],
        [-100, 0]
      )}%)`;
      break;
    case "zoomFade":
      overlayStyle.backgroundColor = "#050505";
      overlayStyle.transform = `scale(${interpolate(
        progress,
        [0, 1],
        [1.2, 1]
      )})`;
      overlayStyle.opacity = easeProgress;
      break;
  }

  return <AbsoluteFill style={overlayStyle} />;
};

/* ========================================================================
   Credits scene (enhanced)
   ======================================================================== */
const CreditsScene: React.FC<{
  logoSrc?: string | null;
  brandingImage?: string | null;
}> = ({ logoSrc, brandingImage }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const totalFrames = fps * 3;

  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });
  const slideUp = interpolate(frame, [0, 25], [20, 0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const fadeOut = interpolate(
    frame,
    [totalFrames - 20, totalFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const combinedOpacity = fadeIn * fadeOut;

  /* Product image separate animation: delayed entrance + subtle scale */
  const productFadeIn = interpolate(frame, [10, 35], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const productScale = interpolate(frame, [10, 35], [0.92, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const productSlideUp = interpolate(frame, [10, 35], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const productFadeOut = interpolate(
    frame,
    [totalFrames - 20, totalFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(ellipse at 50% 40%, #111118 0%, #050505 100%)",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 28,
          opacity: combinedOpacity,
          transform: `translateY(${slideUp}px)`,
        }}
      >
        {/* Product / branding image -- shown prominently only here */}
        {brandingImage && (
          <div
            style={{
              opacity: productFadeIn * productFadeOut,
              transform: `translateY(${productSlideUp}px) scale(${productScale})`,
              marginBottom: 12,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 20,
                padding: 20,
                boxShadow:
                  "0 8px 40px rgba(0,0,0,0.4), 0 0 80px rgba(74,222,128,0.06)",
              }}
            >
              <Img
                src={
                  isLocalPath(brandingImage)
                    ? staticFile(brandingImage)
                    : brandingImage
                }
                style={{
                  maxWidth: 340,
                  maxHeight: 220,
                  objectFit: "contain",
                  display: "block",
                }}
              />
            </div>
          </div>
        )}

        {/* Logo in credits */}
        {logoSrc && (
          <Img
            src={isLocalPath(logoSrc) ? staticFile(logoSrc) : logoSrc}
            style={{
              width: 100,
              objectFit: "contain",
              marginBottom: 8,
              opacity: 0.8,
            }}
          />
        )}
        {/* Divider */}
        <div
          style={{
            width: 48,
            height: 2,
            borderRadius: 1,
            background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)",
          }}
        />
        <span
          style={{
            color: "rgba(255,255,255,0.4)",
            fontSize: 18,
            fontFamily:
              "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
            fontWeight: 400,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}
        >
          Photos / Videos from Pexels
        </span>
      </div>
    </AbsoluteFill>
  );
};

/* ========================================================================
   Logo overlay (persistent, enhanced)
   ======================================================================== */
const LogoOverlay: React.FC<{ logoSrc: string }> = ({ logoSrc }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 20], [0, 0.85], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        top: 40,
        right: 48,
        zIndex: 9999,
        pointerEvents: "none",
        opacity,
      }}
    >
      <div
        style={{
          background: "rgba(0,0,0,0.25)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          borderRadius: 12,
          padding: 12,
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <Img
          src={isLocalPath(logoSrc) ? staticFile(logoSrc) : logoSrc}
          style={{
            width: 120,
            objectFit: "contain",
            display: "block",
          }}
        />
      </div>
    </div>
  );
};

/** Branding image overlay (persistent, bottom-left, enhanced) */
const BrandingImageOverlay: React.FC<{ brandingImage: string }> = ({
  brandingImage,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 25], [0, 0.9], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: 40,
        right: 48,
        zIndex: 9000,
        pointerEvents: "none",
        opacity,
      }}
    >
      <div
        style={{
          background: "rgba(0,0,0,0.2)",
          backdropFilter: "blur(10px)",
          WebkitBackdropFilter: "blur(10px)",
          borderRadius: 10,
          padding: 10,
          border: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <Img
          src={
            isLocalPath(brandingImage)
              ? staticFile(brandingImage)
              : brandingImage
          }
          style={{
            width: 240,
            objectFit: "contain",
            display: "block",
          }}
        />
      </div>
    </div>
  );
};

/* ========================================================================
   Main Composition with transition support (enhanced)
   ======================================================================== */
export const PharmaVideo: React.FC<PharmaVideoProps> = ({
  scenes,
  branding,
}) => {
  const { fps } = useVideoConfig();

  let from = 0;
  const logoSrc =
    branding?.logos && branding.logos.length > 0 ? branding.logos[0] : null;
  const brandingImage =
    branding?.images && branding.images.length > 0
      ? branding.images[0]
      : null;

  return (
    <AbsoluteFill style={{ backgroundColor: "#050505" }}>
      {scenes.map((scene, index) => {
        const durationFrames = Math.max(
          1,
          Math.ceil(scene.duration_sec * fps)
        );

        const start = from;
        from += durationFrames;

        const nextScene =
          index < scenes.length - 1 ? scenes[index + 1] : null;
        const hasTransition = nextScene?.animation?.transition;

        return (
          <React.Fragment key={scene.scene_id}>
            <Sequence from={start} durationInFrames={durationFrames}>
              <SceneVisual
                scene={scene}
                durationFrames={durationFrames}
                logoSrc={logoSrc}
                sceneIndex={index}
                totalScenes={scenes.length}
              />
            </Sequence>

            {/* Render transition overlay if needed */}
            {hasTransition && (
              <TransitionOverlay
                from={start + durationFrames}
                transitionDuration={
                  (nextScene.animation?.transition?.duration_sec ?? 0.5) * fps
                }
                transitionType={
                  nextScene.animation?.transition?.type ?? "fade"
                }
              />
            )}
          </React.Fragment>
        );
      })}

      {/* Credits */}
      <Sequence from={from} durationInFrames={fps * 3}>
        <CreditsScene logoSrc={logoSrc} brandingImage={brandingImage} />
      </Sequence>

      {/* Persistent logo overlay */}
      {logoSrc && <LogoOverlay logoSrc={logoSrc} />}
    </AbsoluteFill>
  );
};
