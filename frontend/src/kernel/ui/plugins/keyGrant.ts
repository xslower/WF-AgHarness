
import { confirmDialog } from "../dialog";


export async function askKeyGrants(pluginId: string,
                                   requested: string[] | undefined
): Promise<string[] | null> {
  const keys = requested || [];
  if (!keys.length) return [];
  const ok = await confirmDialog({
    title: `安装 ${pluginId} · 密钥访问许可`,
    message: `该插件申请读取以下前缀下系统 provider 的 API key：${keys.join("、")}。`
      + "每一项按设置页里 provider「名称」的前缀匹配（不是 id / 模型名、不是子串），"
      + "同一前缀下的多账号会全部提供；允许申请系统里还没配置的 provider（预申请），"
      + "以后添加同前缀 provider 即自动生效，无需重装。"
      + "密钥由系统加密保存，插件仅在发请求时由代码使用，不会展示给模型。"
      + "是否逐项允许？",
    okText: `允许 ${keys.length} 项并安装`,
    danger: true,
  });
  return ok ? keys : null;
}
