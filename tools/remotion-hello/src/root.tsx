import { registerRoot } from "remotion";
import { Composition } from "remotion";
import { HelloWorld } from "./index";

const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="hello-world"
      component={HelloWorld}
      durationInFrames={150}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};

registerRoot(RemotionRoot);
