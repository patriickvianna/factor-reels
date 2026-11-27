import React from "react";
import { Composition } from "remotion";
import { Reel } from "./Reel";
import type { ReelProps } from "./types";
import demo from "./demo.json";
import { Explica } from "./explica/Explica";
import type { ExplicaProps } from "./explica/types";

const explicaDefault: ExplicaProps = { tema: "airfryer", titulo: "Como funciona a air fryer", lines: [], cues: {}, audio: "", duration: 10, handle: "@factorofertas" };

export const Root: React.FC = () => (
  <>
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
    {/* Reels explicativo em 3D (GUT #112) */}
    <Composition
      id="Explica3D"
      component={Explica}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={300}
      defaultProps={explicaDefault}
      calculateMetadata={({ props }) => ({ durationInFrames: Math.max(30, Math.ceil(props.duration * 30)) })}
    />
  </>
);
