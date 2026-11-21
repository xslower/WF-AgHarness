
import { useCallback, useState } from "react";
import { alertDialog } from "../dialog";


export const MAX_ATTACHMENTS = 8;


const DOC_EXTS = new Set([
  "txt", "md", "json", "csv", "log", "py", "js", "ts", "tsx", "jsx",
  "html", "css", "yml", "yaml", "toml", "ini", "sh", "sql", "xml",
  "go", "rs", "java", "c", "h", "cpp",
]);

export interface FileAttachments {
  images: string[];
  setImages: React.Dispatch<React.SetStateAction<string[]>>;
  docs: { name: string; text: string }[];
  setDocs: React.Dispatch<React.SetStateAction<{ name: string; text: string }[]>>;
  addFiles: (files: File[]) => void;
  clear: () => void;
}

export function useFileAttachments(): FileAttachments {
  const [images, setImages] = useState<string[]>([]);
  const [docs, setDocs] = useState<{ name: string; text: string }[]>([]);

  const addFiles = useCallback((files: File[]) => {
    for (const f of files.slice(0, MAX_ATTACHMENTS)) {
      if (f.type.startsWith("image/")) {
        const r = new FileReader();
        r.onload = () => setImages((a) => [...a, r.result as string].slice(0, MAX_ATTACHMENTS));
        r.readAsDataURL(f);
      } else {
        const ext = f.name.split(".").pop()?.toLowerCase() || "";
        if (!DOC_EXTS.has(ext)) {
          void alertDialog(
            `不支持的附件格式：${f.name}（支持图片与 ${[...DOC_EXTS].join("/")} 文档）`);
          continue;
        }
        const r = new FileReader();
        r.onload = () => setDocs((a) => [...a, { name: f.name, text: r.result as string }]
          .slice(0, MAX_ATTACHMENTS));
        r.readAsText(f);
      }
    }
  }, []);

  const clear = useCallback(() => { setImages([]); setDocs([]); }, []);

  return { images, setImages, docs, setDocs, addFiles, clear };
}
