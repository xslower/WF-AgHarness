
import type { ChatMessage } from "../../api";
import { normalizeSpec } from "../../model/modelSpec";

export interface TurnInput {
  body: string;
  images: string[];
  audio: string;
  attachments: { name: string; text: string }[];
  workflow?: string;
  plan?: boolean;
  
  model?: string;
  
  policy?: string;
}


export function makeQid(now: number = Date.now()): string {
  return `c${now.toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}


export function makePayload(input: TurnInput, qid: string): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    type: "chat",
    qid,
    content: input.body,
    images: input.images,
    audio: input.audio,
    attachments: input.attachments,
    model: normalizeSpec(input.model),
    policy: input.policy || "",
  };
  if (input.workflow) payload.workflow = input.workflow;
  if (input.plan !== undefined) payload.plan = input.plan;
  return payload;
}


export function makeUserMessage(body: string, images: string[],
                               attachments: { name: string }[]): ChatMessage {
  const shown = attachments.length
    ? body + (body ? "\n" : "") + attachments.map((a) => `📎 ${a.name}`).join("\n")
    : body;
  if (!images.length) return { role: "user", content: shown };
  return {
    role: "user",
    content: [
      { type: "text", text: shown },
      ...images.map((url) => ({ type: "image_url", image_url: { url } })),
    ],
  } as ChatMessage;
}


export function isEmptyTurn(input: Pick<TurnInput, "body" | "images" | "attachments">): boolean {
  return !input.body.trim() && !input.images.length && !input.attachments.length;
}
