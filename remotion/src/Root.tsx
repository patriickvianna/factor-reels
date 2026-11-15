import React from "react";
import { Composition } from "remotion";
import { Reel } from "./Reel";
import type { ReelProps } from "./types";
import demo from "./demo.json";

export const Root: React.FC = () => (
  <Composition
    id="Reel"
    component={Reel}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={300}
    defaultProps={demo as unknown as ReelProps}
    calculateMetadata={({ props }) => ({ durationInFrames: Math.max(30, Math.ceil(props.duration * 30)) })}
  />
);
