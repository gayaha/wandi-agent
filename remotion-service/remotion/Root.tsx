import { Composition } from "remotion";
import { ReelTemplate } from "./ReelTemplate.js";
import { ReelInputSchema } from "./schemas.js";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="ReelTemplate"
      component={ReelTemplate}
      durationInFrames={90 * 30}
      fps={30}
      width={1080}
      height={1920}
      schema={ReelInputSchema}
      defaultProps={{
        sourceVideoUrl: "https://example.com/sample.mp4",
        hookText: "הנה הטריק שישנה לך את העסק",
        bodyText: "גלה איך להגדיל מכירות ב-30 יום בלבד",
        textDirection: "rtl" as const,
        animationStyle: "fade" as const,
        durationInSeconds: 15,
      }}
    />
  );
};
