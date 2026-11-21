
export type CopyReason = "empty" | "insecure" | "permission" | "failed";

export interface CopyFailure {
  ok: false;
  reason: CopyReason;
  
  hint: string;
}

export type CopyResult = { ok: true } | CopyFailure;


const INSECURE_HINT =
  "当前页面不是安全上下文，浏览器禁用了剪贴板。请用 https:// 或 http://localhost 访问后重试。";

const PERMISSION_HINT =
  "剪贴板权限被 Chrome 拒绝：点复制这个动作本身才会触发浏览器的权限申请，"
  + "若此前已选过「禁止」，请点地址栏左侧图标 → 网站设置 → 剪贴板 → 改为「允许」，"
  + "然后回到页面重新点复制。";

const FAILED_HINT = "复制失败：可手动选中内容后按 Ctrl/Cmd+C。";


export function clipboardState(): "ok" | "insecure" | "unknown" {
  if (typeof window === "undefined") return "unknown";
  return window.isSecureContext ? "ok" : "insecure";
}


export async function clipboardPermission(): Promise<PermissionState | ""> {
  try {
    const p = await navigator.permissions?.query(
      { name: "clipboard-write" as PermissionName });
    return p?.state ?? "";
  } catch {
    return "";
  }
}


function legacyCopy(text: string): boolean {
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.cssText = "position:fixed;top:-1000px;left:-1000px;opacity:0";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    return ok;
  } catch {
    return false;
  }
}

export async function copyText(text: string): Promise<CopyResult> {
  if (!text) return { ok: false, reason: "empty", hint: "没有可复制的内容" };
  const insecure = clipboardState() === "insecure";
  let deniedByApi = false;
  if (!insecure) {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        return { ok: true };
      }
    } catch (e) {
      deniedByApi = e instanceof DOMException
        && (e.name === "NotAllowedError" || e.name === "SecurityError");
    }
  }
  if (legacyCopy(text)) return { ok: true };
  const perm = await clipboardPermission();
  if (insecure) return { ok: false, reason: "insecure", hint: INSECURE_HINT };
  if (perm === "denied" || deniedByApi) {
    return { ok: false, reason: "permission", hint: PERMISSION_HINT };
  }
  return { ok: false, reason: "failed", hint: FAILED_HINT };
}
