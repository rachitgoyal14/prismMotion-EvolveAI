import { Composition } from "remotion";
import { PharmaVideo } from "./PharmaVideo";

const FPS = 30;
const WIDTH = 1920;
const HEIGHT = 1080;

const defaultScenes = [
  {
    scene_id: 1,
    duration_sec: 5,
    concept: "Placeholder",
    script: "Welcome.",
    image: { src: "https://images.pexels.com/photos/356040/pexels-photo-356040.jpeg?auto=compress&cs=tinysrgb&w=1920", alt: "Placeholder" },
    video: null,
  },
];

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="PharmaVideo"
        component={PharmaVideo}
        durationInFrames={FPS * 90}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{
          scenes: defaultScenes,
        }}
        calculateMetadata={({ props }) => {
          const totalSec = props.scenes.reduce((s: number, c: { duration_sec: number }) => s + c.duration_sec, 0);
          return {
            durationInFrames: Math.ceil(totalSec * FPS) + FPS * 3,
          };
        }}
      />
    </>
  );
};
