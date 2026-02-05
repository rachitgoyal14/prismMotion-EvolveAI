import { Composition, getInputProps } from "remotion";
import { PharmaVideo, calculateMetadata, PharmaVideoProps } from "./PharmaVideo";

const FPS = 30;
const WIDTH = 1920;
const HEIGHT = 1080;

const defaultScenes: PharmaVideoProps["scenes"] = [
  {
    scene_id: 1,
    duration_sec: 5,
    concept: "Placeholder",
    script: "Welcome.",
    image: {
      src: "https://images.pexels.com/photos/356040/pexels-photo-356040.jpeg?auto=compress&cs=tinysrgb&w=1920",
      alt: "Placeholder",
    },
    video: null,
    audio_src: null,
  },
];

export const Root: React.FC = () => {
  // Props passed from CLI (`--props=...`) or Remotion Studio.
  // `getInputProps` is untyped in this Remotion version, so we narrow manually.
  const rawInput = getInputProps() as unknown;
  const inputProps = rawInput as Partial<PharmaVideoProps> | null;

  const scenes =
    inputProps &&
    Array.isArray(inputProps.scenes) &&
    inputProps.scenes.length > 0
      ? (inputProps.scenes as PharmaVideoProps["scenes"])
      : defaultScenes;

  return (
    <Composition
      id="PharmaVideo"
      component={PharmaVideo}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{
        scenes,
      }}
      calculateMetadata={calculateMetadata}
    />
  );
};
