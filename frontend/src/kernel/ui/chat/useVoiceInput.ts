
import { useCallback, useRef, useState } from "react";
import { alertDialog } from "../dialog";

export interface VoiceInput {
  recording: boolean;
  
  audio: string;
  setAudio: (v: string) => void;
  toggleRecord: () => Promise<void>;
}

export function useVoiceInput(): VoiceInput {
  const [recording, setRecording] = useState(false);
  const [audio, setAudio] = useState("");
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const toggleRecord = useCallback(async () => {
    if (recording) {
      mediaRef.current?.stop();
      return;
    }
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        void alertDialog("当前环境不支持录音（需要 HTTPS 或 localhost）");
        return;
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (ev) => { if (ev.data.size) chunksRef.current.push(ev.data); };
      mr.onstop = () => {
        try {
          stream.getTracks().forEach((t) => t.stop());
          const blob = new Blob(chunksRef.current, { type: mr.mimeType || "audio/webm" });
          if (!blob.size) { setRecording(false); return; }
          const rd = new FileReader();
          rd.onload = () => {
            
            const r = rd.result;
            if (typeof r === "string" && r.startsWith("data:")) setAudio(r);
          };
          rd.onerror = () => {  };
          rd.readAsDataURL(blob);
        } finally {
          setRecording(false);
        }
      };
      mr.start();
      mediaRef.current = mr;
      setRecording(true);
    } catch (e) { void alertDialog(`录音失败: ${e}`); setRecording(false); }
  }, [recording]);

  return { recording, audio, setAudio, toggleRecord };
}
