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

/* Scene visual with animation support */
const SceneVisual: React.FC<{ scene: Scene; durationFrames: number;logoSrc?: string|null}> = ({
  scene,
  durationFrames,
  logoSrc
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const animConfig = scene.animation;
  const entranceDuration =
    (animConfig?.entrance?.duration_sec ?? 0.5) * fps;
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

  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a" }}>
      {scene.audio_src && <Audio src={staticFile(scene.audio_src)} />}

      {scene.video?.src ? (
        <OffthreadVideo
          src={isLocalPath(scene.video.src) ? staticFile(scene.video.src) : scene.video.src}
          style={mediaStyle}
        />
      ) : scene.image?.src ? (
        <Img
          src={isLocalPath(scene.image.src) ? staticFile(scene.image.src) : scene.image.src}
          alt={scene.image.alt ?? ""}
          style={mediaStyle}
        />
      ) : (
        <AbsoluteFill
          style={{
            justifyContent: "center",
            alignItems: "center",
            backgroundColor: "#222",
          }}
        >
          <span style={{ color: "#fff" }}>Missing media</span>
        </AbsoluteFill>
      )}

      <AbsoluteFill
        style={{
          justifyContent: "flex-end",
          padding: 48,
          background:
            "linear-gradient(transparent 40%, rgba(0,0,0,0.75) 100%)",
        }}
      >
        <div
          style={{
            color: "#fff",
            fontSize: 32,
            fontFamily: "sans-serif",
            maxWidth: 900,
          }}
        >
          {scene.script}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* Transition overlay between scenes */
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
  };

  switch (transitionType) {
    case "fade":
      overlayStyle.backgroundColor = `rgba(0, 0, 0, ${easeProgress})`;
      break;
    case "slideLeft":
      overlayStyle.backgroundColor = "#000";
      overlayStyle.transform = `translateX(${interpolate(
        progress,
        [0, 1],
        [100, 0]
      )}%)`;
      break;
    case "slideRight":
      overlayStyle.backgroundColor = "#000";
      overlayStyle.transform = `translateX(${interpolate(
        progress,
        [0, 1],
        [-100, 0]
      )}%)`;
      break;
    case "slideUp":
      overlayStyle.backgroundColor = "#000";
      overlayStyle.transform = `translateY(${interpolate(
        progress,
        [0, 1],
        [100, 0]
      )}%)`;
      break;
    case "slideDown":
      overlayStyle.backgroundColor = "#000";
      overlayStyle.transform = `translateY(${interpolate(
        progress,
        [0, 1],
        [-100, 0]
      )}%)`;
      break;
    case "zoomFade":
      overlayStyle.backgroundColor = "#000";
      overlayStyle.transform = `scale(${interpolate(progress, [0, 1], [1.2, 1])})`;
      overlayStyle.opacity = easeProgress;
      break;
  }
  

  return <AbsoluteFill style={overlayStyle} />;
};

/* ------------------ Main Composition with transition support ------------------ */
export const PharmaVideo: React.FC<PharmaVideoProps> = ({ scenes ,branding}) => {
  const { fps } = useVideoConfig();

  let from = 0;
  const logoSrc =
  branding?.logos && branding.logos.length > 0
    ? branding.logos[0]
    : null;


  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {scenes.map((scene, index) => {
        const durationFrames = Math.max(
          1,
          Math.ceil(scene.duration_sec * fps)
        );

        const start = from;
        from += durationFrames;

        const nextScene = index < scenes.length - 1 ? scenes[index + 1] : null;
        const hasTransition = nextScene?.animation?.transition;

        return (
          <React.Fragment key={scene.scene_id}>
            <Sequence
              from={start}
              durationInFrames={durationFrames}
            >
              <SceneVisual scene={scene} durationFrames={durationFrames}  logoSrc={logoSrc}/>
            </Sequence>

            {/* Render transition overlay if needed */}
            {hasTransition && (
              <TransitionOverlay
                from={start + durationFrames}
                transitionDuration={
                  (nextScene.animation?.transition?.duration_sec ?? 0.5) * fps
                }
                transitionType={nextScene.animation?.transition?.type ?? "fade"}
              />
            )}
          </React.Fragment>
        );
      })}

      {/* Credits */}
      <Sequence from={from} durationInFrames={fps * 3}>
        <AbsoluteFill
          style={{
            backgroundColor: "#111",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <span style={{ color: "#888", fontSize: 24 }}>
            Photos / Videos from Pexels
          </span>
        </AbsoluteFill>
      </Sequence>
      {logoSrc && (
  <Img
    src={staticFile(logoSrc)}
    style={{
      position: "absolute",
      top: 40,
      right: 40,
      width: 140,
      opacity: 0.9,
      pointerEvents: "none",
      zIndex: 9999
    }}
  />
)}

    </AbsoluteFill>
  );
};