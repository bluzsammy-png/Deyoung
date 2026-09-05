/**
 * The DeYoung model lineup - public identity for the render pipeline.
 *
 * Honesty rules (do not fabricate):
 *  - Every model maps to REAL capability the engine ships today.
 *  - "gpu" tier needs the free local GPU supply (Kaggle/own-PC workers running
 *    LTX-Video). When no GPU worker is online those jobs wait in queue - the UI
 *    says so instead of pretending.
 *  - deyo-Max routes queue priority and the full assemble pipeline (script,
 *    scenes, voice, music, captions, QC) that produced the site's own film.
 */
export type DeyoModel = {
  code: string;
  name: string;
  tagline: string;
  tier: "free" | "gpu" | "flagship";
  queuePriority: number; // added to the plan priority
  secondsCap: number; // max clip length this model accepts
  features: string[];
  flagship?: boolean;
};

export const DEYO_MODELS: DeyoModel[] = [
  {
    code: "deyo.1",
    name: "deyo.1",
    tagline: "The reliable starter - fast local render.",
    tier: "free",
    queuePriority: 0,
    secondsCap: 15,
    features: ["720p", "Script-to-scene boards", "Captions", "Runs on always-on local render"],
  },
  {
    code: "deyo.1-pro",
    name: "deyo.1 pro",
    tagline: "Starter + polish: captions, score mix, brand watermark.",
    tier: "free",
    queuePriority: 1,
    secondsCap: 15,
    features: ["720p", "Caption typography", "Music bed & mix", "Priority over deyo.1"],
  },
  {
    code: "deyo.2",
    name: "deyo.2",
    tagline: "True AI video generation on the free GPU lane.",
    tier: "gpu",
    queuePriority: 2,
    secondsCap: 30,
    features: ["720p AI footage", "LTX engine on GPU workers", "Scene prompts expanded", "Queue when GPU lane is busy"],
  },
  {
    code: "deyo.2-pro",
    name: "deyo.2 pro",
    tagline: "AI footage with sound design & longer takes.",
    tier: "gpu",
    queuePriority: 3,
    secondsCap: 45,
    features: ["720p AI footage", "Audio bed + mix", "Up to 45s takes", "Priority over deyo.2"],
  },
  {
    code: "deyo.3",
    name: "deyo.3",
    tagline: "High-step render - cleaner motion, safer framing.",
    tier: "gpu",
    queuePriority: 4,
    secondsCap: 60,
    features: ["720p, high-step schedule", "Face-safe framing QC", "Auto retry on QA fail", "Priority over deyo.2 pro"],
  },
  {
    code: "deyo.3-pro",
    name: "deyo.3 pro",
    tagline: "High-step render with voice track.",
    tier: "gpu",
    queuePriority: 5,
    secondsCap: 60,
    features: ["720p, high-step schedule", "Voice-over track", "Ducked music mix", "Priority over deyo.3"],
  },
  {
    code: "deyo-max",
    name: "deyo-Max",
    tagline: "Our flagship. The full engine that made our own film.",
    tier: "flagship",
    queuePriority: 9,
    secondsCap: 60,
    flagship: true,
    features: [
      "Full pipeline: script, scenes, voice, music, captions, QC",
      "Top queue priority, always",
      "Up to 60 seconds in one pass",
      "Character & avatar references",
    ],
  },
];

export function getModel(code: string): DeyoModel {
  return DEYO_MODELS.find((m) => m.code === code) ?? DEYO_MODELS[0];
}
