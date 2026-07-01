import { registerRoot } from "remotion";
import { Composition } from "remotion";
import { HelloWorld } from "./index";
import { GuZhenRen } from "./guzhenren";
import { ExamReview } from "./examReview";
import { InformationGap, informationGapDurationFrames } from "./informationGap";
import timings1 from "../../../projects/wangluo-kaoqian/part1/timings.json";
import timings2 from "../../../projects/wangluo-kaoqian/part2/timings.json";

const FPS = 30;
const examDur = (t: { total: number }) => Math.ceil(t.total * FPS) + 30;

const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="hello-world"
        component={HelloWorld}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="guzhenren"
        component={GuZhenRen}
        durationInFrames={900}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="exam-part1"
        component={ExamReview}
        durationInFrames={examDur(timings1)}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ timings: timings1 }}
      />
      <Composition
        id="exam-part2"
        component={ExamReview}
        durationInFrames={examDur(timings2)}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ timings: timings2 }}
      />
      <Composition
        id="information-gap"
        component={InformationGap}
        durationInFrames={informationGapDurationFrames}
        fps={FPS}
        width={1920}
        height={1080}
      />
      <Composition
        id="information-gap-vertical"
        component={InformationGap}
        durationInFrames={informationGapDurationFrames}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{ vertical: true }}
      />
    </>
  );
};

registerRoot(RemotionRoot);
