import React from "react";
import {
  AbsoluteFill,
  Sequence,
  Img,
  useVideoConfig,
  OffthreadVideo,
  Audio,
  staticFile,
} from "remotion";

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
};

export type PharmaVideoProps = {
  scenes: Scene[];
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

/* ------------------ Helper to determine if path is local or remote ------------------ */
const isLocalPath = (src: string): boolean => {
  return !src.startsWith("http://") && !src.startsWith("https://");
};

/* ------------------ Scene visual only (NO sequencing here) ------------------ */
const SceneVisual: React.FC<{ scene: Scene }> = ({ scene }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a" }}>
      {scene.audio_src && <Audio src={staticFile(scene.audio_src)} />}

      {scene.video?.src ? (
        <OffthreadVideo
          src={isLocalPath(scene.video.src) ? staticFile(scene.video.src) : scene.video.src}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : scene.image?.src ? (
        <Img
          src={isLocalPath(scene.image.src) ? staticFile(scene.image.src) : scene.image.src}
          alt={scene.image.alt ?? ""}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
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

/* ------------------ Main Composition ------------------ */
export const PharmaVideo: React.FC<PharmaVideoProps> = ({ scenes }) => {
  const { fps } = useVideoConfig();

  let from = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {scenes.map((scene) => {
        const durationFrames = Math.max(
          1,
          Math.ceil(scene.duration_sec * fps)
        );

        const start = from;
        from += durationFrames;

        return (
          <Sequence
            key={scene.scene_id}
            from={start}
            durationInFrames={durationFrames}
          >
            <SceneVisual scene={scene} />
          </Sequence>
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
    </AbsoluteFill>
  );
};