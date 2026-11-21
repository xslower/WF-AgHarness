from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...workflow.nodes.registry import NodeRegistry

pass
_ACTIONS: dict[str, dict] = {
    "list": {"need": "—", "does": "列出当前项目下所有工作流（名称/描述/节点数）",
             "ret": '[{"name": "日报生成", "desc": "...", "nodes": 3}]'},
    "help": {"need": "—（topic 可选）", "does": "本帮助。topic 可填动作名、节点类型或 recipe",
             "ret": "纯文本说明"},
    "run": {"need": "name（input 可选）", "does": "后台启动工作流，立即返回 run_id（不等跑完）",
            "ret": '{"run_id","status","nodes":[...],"ok":true}；启动体检不过={"error": "..."}'},
    "wait": {"need": "id（timeout/detail 可选）", "does": "等后台运行跑完：好了给最终输出，超时只结束本次等待",
             "ret": '跑完=最终输出文本；detail=true={..."final","nodes":[...]}；未完成/超时={..."timed_out":true}'},
    "get": {"need": "name", "does": "读取工作流的完整 JSON 定义（含 nodes/edges/inputs）",
            "ret": '{"name","desc","inputs","nodes":[...],"edges":[...]}'},
    "list_node": {"need": "name", "does": "只列节点摘要（id/type/next/字段），比 get 省 token",
                  "ret": '[{"id","type","next","fields":{...}}]'},
    "add_node": {"need": "name, node", "does": "追加一个节点（改内存，需 save 落盘）",
                 "ret": '{"ok": true, "nodes": 4, "next": "..."}'},
    "edit_node": {"need": "name, node_id, fields", "does": "改节点字段，合并更新（改内存）",
                  "ret": '{"ok": true, "node": {...}}'},
    "del_node": {"need": "name, node_id", "does": "删节点并清理指向它的连线（改内存）",
                 "ret": '{"ok": true, "nodes": 3}'},
    "save": {"need": "name（workflow 可选）", "does": "落盘。传 workflow=完整定义则创建或整体覆盖，"
                                                    "不传则保存前面的内存改动",
             "ret": '{"ok": true, "name": "...", "nodes": 3}'},
}

pass
_RULES = [
    "nodes 是有序列表，运行时从 nodes[0] 开始、按 next 依次走 —— 第一个节点就是入口，不需要 start 节点。",
    "连线只有四种，值都是节点 id：next=普通后继；true/false=condition 的两个分支"
    "（true 必填，false 可空=到此结束）；body=loop/map 子链的起点。next 留空表示结束。"
    "`next: [A, B]`（数组）= 扇出，等价画布上画两条出边；实际并行与否由运行参数 parallel 决定，"
    "不要和 condition/human/map 混用（会直接报错，改用 map 或拆子工作流）。"
    "condition 的 true 指回上游节点就是「循环」（回边），用 maxVisits 限制进入次数。",
    "变量：${inputs.名称} 取运行输入；${节点id} 取该节点输出；${prev} 上一个节点的输出；"
    "循环内另有 ${__i__}（轮次，从 0 起）和 ${__item__}（map 当前项）。"
    "JSON 输出取字段用 ${节点id.字段}（支持多级与列表下标），不必再插 code 节点；"
    "往 JSON / Python 代码 / URL 里插值必须用过滤器：${x|json}（带引号已转义的 JSON 字符串）、"
    "${x|py}（Python 字面量）、${x|url}（百分号编码）；文档里想写字面量用 $${x}。"
    "未定义的变量会直接报错（带最相近的名字），不再原样保留。"
    "路径/文件名字段（write.path、exec.command 等）会自动去掉 JSON 字符串的外层引号，"
    "所以 out/${s1}/r.md 直接可用；角色设定用 llm 的 system 字段（docs 只放规则文档）。",
    "需要人拍板（要不要开始烧钱、这张图能不能渲染）用 human 节点：title + options"
    "（每行一个按钮），选第 1 项走 true、其余走 false，没写 true/false 就走 next"
    "（三样都没有会在启动前报错）；它不是 handoff —— handoff 只交接/结束，"
    "不会停下来等人。agent 工具触发的工作流遇 human 会直接拒启动，自动化请传 human=auto-approve。",
    "图撑大时拆成子工作流：用 workflow 节点（name/inputsJson/output）调另一个工作流；"
    "子工作流只看到自己传进去的 inputs，限深 3 层、禁止同名循环调用。",
    "exec/code 遇非零退出码默认终止流程；如果是「门禁不通过」这类正常业务信号，"
    "给节点加 allowFail: true，输出里保留 [exit N]，后续用 condition 自己判。"
    "exec/code 的 timeout 单位是秒（不写默认 600），向上写到毫秒级的任务自己改大。",
    "输出不会在数据层被截断（节点输出完整落盘，下游 llm 超长时自动转文件引用）；"
    "但单节点输出有 8MB 硬顶，超了要改成「写文件 + 只传路径」。",
    "add_node/edit_node/del_node 只改内存草稿，**必须再 save 才落盘**；只想看清结构用 get/list_node。",
    "新建工作流优先一次 save 传完整 workflow（一次成型），不要先存空壳再逐个 add_node。",
    "把新节点接到流程里要两步：add_node 加节点 + edit_node 改上游的 next 指向它，否则它是孤岛、run 不会执行。",
    "run 失败返回 {\"error\": ...}，先看报错里的节点 id，用 list_node 核对该节点必填字段是否为空。"
    "启动前会集中体检：未定义变量 / type 缺失 / 必填字段空 / human 无出口 / docs 找不到 /"
    "子工作流不存在 / python import 不可解析 —— 一次性报完，一个节点都不跑（不会烧钱）。",
    "用户说「建/改个工作流」「做个自动化流程」时，必须真的 save 落盘 —— 不要用 write 手工写个脚本"
    "或把流程在回复里描述一遍就算完成，那样用户拿不到可复用的工作流。",
]

pass
pass
pass


def _req_keys(spec) -> list[str]:
    return list(dict.fromkeys(
        [*spec.required, *[f.key for f in spec.fields if f.required]]))


def _extra_keys(spec) -> list[str]:
    keys = {f.key for f in spec.fields}
    declared = list(getattr(spec, "branch_keys", ()) or ())
    if declared:
        return [k for k in declared if k not in keys]
    return [k for k in _req_keys(spec) if k not in keys]

pass
_RECIPES: list[dict] = [
    {
        "id": "create",
        "title": "案例 1：从零建一个工作流并跑通",
        "when": "用户要「做个 X 工作流」，而 action=list 里没有合适的",
        "types": ["llm", "write"],
        "actions": ["save", "run"],
        "body": """\
场景：把素材整理成一份 markdown 日报。

第一步，一次 save 传完整定义（不要先存空壳）：
{"action":"save","name":"日报生成","workflow":{
  "name":"日报生成","desc":"把素材整理成 markdown 日报",
  "inputs":[{"name":"input","desc":"原始素材","type":"text"}],
  "nodes":[
    {"id":"s1","type":"llm",
     "prompt":"把下面的素材整理成 markdown 日报，含「今日完成／问题／明日计划」三节：\\n${inputs.input}",
     "next":"w1"},
    {"id":"w1","type":"write","path":"out/日报.md","content":"${s1}"}
  ]}}

第二步，运行（input 会填进 ${inputs.input}）：
{"action":"run","name":"日报生成","input":"今天修了登录超时……"}

要点：nodes 顺序即执行顺序；s1 的 next 指向 w1；w1 没有 next，跑完即结束。""",
    },
    {
        "id": "patch",
        "title": "案例 2：在已有工作流上接着改",
        "when": "用户要求「加一步」「改提示词」「换个输出路径」",
        "types": ["llm", "write"],
        "actions": ["list_node", "add_node", "edit_node", "del_node", "save"],
        "body": """\
先看清结构（别凭记忆改）：
{"action":"list_node","name":"日报生成"}

在末尾接一个新节点（两步，缺一不可）：
{"action":"add_node","name":"日报生成",
 "node":{"id":"w2","type":"write","path":"out/日报-备份.md","content":"${s1}"}}
{"action":"edit_node","name":"日报生成","node_id":"w1","fields":{"next":"w2"}}

只改提示词（fields 只写要动的键，其它保持不变；值设 null 表示删掉该键）：
{"action":"edit_node","name":"日报生成","node_id":"s1",
 "fields":{"prompt":"用英文写日报：${inputs.input}"}}

删节点（会自动清掉指向它的 next/true/false/body 引用）：
{"action":"del_node","name":"日报生成","node_id":"w2"}

最后必须落盘，否则全丢：
{"action":"save","name":"日报生成"}
save 返回 {"ok":true,"nodes":3} 才算成功；返回 error 说明结构非法，按提示改。""",
    },
    {
        "id": "branch",
        "title": "案例 3：条件分支（condition）",
        "when": "要按内容走不同路线：分类、紧急/普通、长短文本分流",
        "types": ["condition", "llm", "write"],
        "actions": ["save"],
        "body": """\
condition 有 true 与 false 两个出口：true 必填（条件成立走哪），false 可空（空 = 直接结束）。
要「条件循环」就把 true 指回上游节点形成回边，再用 maxVisits 限制进入次数（没有独立 while 节点）：
- mode="expr"：expr 是表达式，用 eval 语义，如 len(${prev}) > 100、'error' in ${s1}
- mode="llm" ：expr 是自然语言条件，如「内容属于紧急故障」，由模型判断真假
- input 是要判断的内容，默认 ${prev}（上一节点输出），也可写 ${s1} / ${inputs.input}

{"action":"save","name":"工单分流","workflow":{
  "name":"工单分流","desc":"紧急工单单独出文件",
  "inputs":[{"name":"input","desc":"工单原文","type":"text"}],
  "nodes":[
    {"id":"s1","type":"llm","prompt":"提取工单要点：${inputs.input}","next":"c1"},
    {"id":"c1","type":"condition","mode":"llm","expr":"内容属于紧急故障",
     "input":"${s1}","true":"t1","false":"f1"},
    {"id":"t1","type":"write","path":"out/紧急.md","content":"${s1}"},
    {"id":"f1","type":"write","path":"out/普通.md","content":"${s1}"}
  ]}}

要点：true/false 那两个节点自己不用再接 next；c1 之外的节点都按 next 走。""",
    },
    {
        "id": "tools",
        "title": "案例 4：让 llm 节点自己用工具（读目录、搜索、跑命令）",
        "when": "任务需要「先自己找资料再总结」，路径事先不确定",
        "types": ["llm"],
        "actions": ["save"],
        "body": """\
llm 节点的 tools 字段控制可用工具：
- "auto"（默认）= 全部工具，模型自己决定读哪个文件、搜什么
- "f_read,grep,web_search" = 白名单，只给这几个
- "off" = 纯对话，不调工具

{"action":"save","name":"文档汇总","workflow":{
  "name":"文档汇总","desc":"读 docs/ 下全部文档并汇总",
  "inputs":[{"name":"input","desc":"汇总侧重点","type":"text"}],
  "nodes":[
    {"id":"s1","type":"llm","tools":"auto",
     "prompt":"读取 docs/ 目录下的所有 markdown 文件（先用工具列目录），按「${inputs.input}」的要求汇总，输出到 out/汇总.md",
     "next":""}
  ]}}

对比：若路径是确定的，别让模型自己找 —— 用 docs 字段直接喂文件（每行一个路径），
或前面加读文件节点再用 ${该节点id} 引用，这样更稳、更省 token。""",
    },
    {
        "id": "batch",
        "title": "案例 5：批处理（map 逐项跑子链）",
        "when": "同一套处理要跑在 N 个条目上",
        "types": ["map", "llm"],
        "actions": ["save"],
        "body": """\
map 把 items 拆成一条条，对每条执行 body 子链，子链里用 ${__item__} 取当前项、
${__i__} 取序号；子链最后一个节点不接 next 就会自动回到 map 处理下一项。

并发：map 可写 concurrency（默认 0=跟随全局设置 wfMaxConcurrency，默认 3）。
但运行级并行模式为 sequential（画布上选「顺序」）时一律串行，节点写了也不生效 ——
这项是给「30 镜 × 生图」这种耗时批处理用的，换成允许高并发的 provider 再把
wfMaxConcurrency 调高即可。

{"action":"save","name":"批量简介","workflow":{
  "name":"批量简介","desc":"为每个产品写一句简介",
  "inputs":[{"name":"input","desc":"产品列表，JSON 数组或每行一个","type":"text"}],
  "nodes":[
    {"id":"s1","type":"llm","format":"list",
     "prompt":"把下面的产品名整理成每行一个的列表：${inputs.input}","next":"m1"},
    {"id":"m1","type":"map","items":"${s1}","body":"p1"},
    {"id":"p1","type":"llm","prompt":"为产品「${__item__}」写一句 20 字以内的简介"}
  ]}}

同类写法：loop（固定 N 次，times）；需要「按条件重复」就把 condition 的 true 指回上游
形成回边，并用 maxVisits 收敛（没有独立的 while 节点）。
共同点：body 指向子链的第一个节点 id；子链跑完回到控制节点，再走控制节点的 next。""",
    },
    {
        "id": "debug",
        "title": "案例 6：run 失败怎么查",
        "when": "run 返回 error，或结果不符合预期",
        "types": ["llm", "write", "exec"],
        "actions": ["run", "get", "list_node"],
        "body": """\
按这个顺序排，不要盲改：
1. {"action":"list_node","name":"X"} —— 确认节点在、id 没写错、next 链没断
2. run 的 error 里若带节点 id，就看那个节点：必填字段是否为空、变量名是否拼错
3. 变量拼写核对：${inputs.xxx} 的 xxx 必须在 workflow.inputs 里声明过；
   ${s1} 的 s1 必须是真实节点 id（不是类型名）
4. save 报「结构非法」：多半是 next/true/false/body 指向了不存在的节点 id，
   或节点 id 重复
5. 改了字段却没生效：忘了 save（add/edit/del 只改内存）""",
    },
]

_RECIPE_ALIASES = {"recipe", "recipes", "example", "examples", "案例", "示例", "例子"}
_OVERVIEW_ALIASES = {"help", "all", "overview", "帮助", "用法", "总表", "速查"}


def _match_topic(low: str, names: list[str]) -> tuple[str, list[str]]:
    if low in names:
        return low, []
    for pool in ([n for n in names if n.startswith(low)],
                 [n for n in names if low in n]):
        if len(pool) == 1:
            return pool[0], []
        if len(pool) > 1:
            return "", pool
    return "", []


def _node_fields_short(spec) -> str:
    fields = list(spec.fields)
    req = _req_keys(spec)
    opt = [f.key if not f.options else f"{f.key}({'|'.join(f.options)})"
           for f in fields if f.key not in req]
    parts = []
    if req:
        parts.append("必填 " + ", ".join(req))
    if opt:
        parts.append("可选 " + ", ".join(opt))
    return "｜".join(parts) if parts else "无字段"


def _node_detail(spec) -> str:
    req = _req_keys(spec)
    field_keys = {f.key for f in spec.fields}
    extra = _extra_keys(spec)
    shown = [k for k in req if k in field_keys]
    out = [f"## 节点 {spec.type} — {spec.label}（分组：{spec.group}）"]
    if spec.desc:
        out.append(f"说明：{spec.desc}")
    line = "必填字段：" + (", ".join(shown) if shown else "无")
    if extra:
        line += f"；连线字段 {', '.join(extra)}（值填目标节点 id，不在普通字段表里）"
    out.append(line)
    if spec.fields:
        out.append("字段明细：")
        for f in spec.fields:
            kind = f.kind + ("=" + "|".join(f.options) if f.options else "")
            bits = [f"  - {f.key}", f"[{kind}{', 必填' if f.key in req else ''}]", f.label]
            if f.placeholder:
                bits.append("例: " + f.placeholder.splitlines()[0])
            out.append("  ".join(bits))
    pass
    node = {"id": "s1", "type": spec.type}
    for f in spec.fields:
        if f.key in req:
            node[f.key] = (f.placeholder.splitlines() or [""])[0] or f"{f.key} 的值"
    for k in extra:
        node[k] = f"<{k} 分支的起点节点 id>"
    out.append("最小示例：" + json.dumps(node, ensure_ascii=False))
    out.append("插进流程：add_node 后要 edit_node 把上游 next 指到 s1；节点自己的 next 指向下一个。")
    return "\n".join(out)


def _action_detail(name: str) -> str:
    a = _ACTIONS.get(name)
    if not a:
        return f"未知 action: {name}"
    out = [f"## action={name}", f"作用：{a['does']}",
           f"必填：{a['need']}", f"返回：{a['ret']}"]
    tips = {
        "run": "用 input 传文本，工作流里以 ${inputs.input} 读取；失败先看 error 里的节点 id。"
               "遇到 human 闸门默认直接失败（无人在场），要让它自动走就传 "
               "human=auto-approve 或 auto-reject。"
               "run 是后台启动：拿到 run_id 后必须调 action=wait 才能拿到结果。",
        "wait": "只等后台运行，不中止它。超时返回 timed_out=true 与当前节点进度，"
                "可以再 wait；要中止请去画布运行面板。",
        "save": "传 workflow 时必须有 name 与**非空** nodes 列表，且每个节点有唯一 id、"
                "next/true/false/body 只能指向存在的 id；不传 workflow 就保存内存草稿。",
        "add_node": "node 是完整节点对象：内层 id/type 必填，其余字段名按节点类型给"
                    "（help topic=<节点类型> 查）。加完记得 edit_node 接上游 next，再 save。",
        "edit_node": "fields 只写要改的键，合并更新；值设 null 删除该键；不能改 id（要改就删了重建）。",
        "del_node": "会自动清掉其它节点指向它的 next/true/false/body；删完 save 落盘。",
        "list_node": "拿不准现有节点的 id 或字段时先跑这个，比 get 省一半 token。",
    }
    if name in tips:
        out.append("注意：" + tips[name])
    return "\n".join(out)


def _recipe_block(r: dict) -> str:
    return f"## {r['title']}\n适用：{r['when']}\n\n{r['body']}"


def _overview(specs) -> str:
    out = ["# workflow 工具速查",
           "",
           "## 一、动作（action）"]
    for name, a in _ACTIONS.items():
        out.append(f"  - {name}：必填 {a['need']}｜{a['does']}")
    out += ["", "## 二、通用规则"]
    out += [f"  - {r}" for r in _RULES]
    out += ["", "## 二之二、条件表达式（condition 的 expr）",
            "  - ${x} 拿到的是**字符串**（兼容旧写法）：len(${s1}) > 100、'错' in ${s1}",
            "  - 要比布尔/数字/取字段，用 ${x!raw}（原生值）：${rev.pass!raw} == True、"
            "${s2!raw}['scenes'][0]['shot'] == '开场'。!raw 会先按 JSON、再按 YAML 解析，"
            "所以 format=yaml 的输出也能直接用",
            "  - 助手：json(${x}) 解析 JSON、yaml(${x}) 解析 YAML、get(obj, 'a.b.0', 默认值) 取路径、"
            "boolv(${x}) 人话转布尔（通过/是/true）、num(${x}) 转数字、"
            "match(正则, ${x}) 是否命中；re 模块可用",
            "  - map 的 items 也是同一套表达式：items 写 ${s1!raw}['scenes'] 就直接拿到列表；"
            "纯文本（a, b, c / 每行一个）仍然按旧逻辑拆",
            "  - map 要把 N 轮结果收成数组：节点写 output: json（默认 text），"
            "输出变成 {\"n\",\"items\",\"results\"}，results 是每轮 collect 变量的**原生值**"
            "（JSON 自动解析成对象）—— ${m1.results} 是数组、${m1.results.0.字段} 可下钻，"
            "不用再对拼接文本 split('\\n\\n')。collect 写 body 里产出结果的那个节点 id",
            "  - 表达式写错不会被静默当假：condition 输出的 error 字段会带 SyntaxError 等原文",
            "  - maxVisits 数的是「进入次数」（含首轮）：maxVisits=3 最多重做 2 次；"
            "不写默认 1000（纯防死循环）。到上限按**正常结束**处理（有 false 走 false），"
            "并在运行结果里留一条 warning，不再报错。",
            "  - 输出格式选择：模型能力弱时优先 format=list（每行一项，约束最松、最不容易崩）。"
            "format=json 需顶层对象/数组；format=yaml 试次后仍解析失败会直接报错（不会静默降级）"]
    out += ["", f"## 三、节点类型（{len(specs)} 种）"]
    for s in specs:
        out.append(f"  - {s.type}（{s.label}）{_node_fields_short(s)}")
    out += ["", "## 四、最小可运行模板（把尖括号换成你的内容，改完直接发）",
            '{"action":"save","name":"<工作流名>","workflow":{',
            '  "name":"<工作流名>","desc":"<一句话说明>",',
            '  "inputs":[{"name":"input","desc":"<输入说明>","type":"text"}],',
            '  "nodes":[',
            '    {"id":"s1","type":"llm","prompt":"<任务描述，可写 ${inputs.input}>","next":"w1"},',
            '    {"id":"w1","type":"write","path":"out/result.md","content":"${s1}"}',
            '  ]}}',
            "然后运行（会返回最终输出）：",
            '{"action":"run","name":"<工作流名>","input":"<这次要处理的素材>"}',
            "改现有工作流则用 list_node → add_node/edit_node → save 三步。",
            "", "## 五、看细节",
            '  {"action":"help","topic":"llm"}      某类节点的全部字段 + 最小示例',
            '  {"action":"help","topic":"add_node"} 某个动作的参数与注意事项',
            "  完整案例（help topic=recipe）：" + "；".join(r["title"].split("：")[-1]
                                                          for r in _RECIPES),
            '  当前项目有哪些工作流：{"action":"list"}']
    return "\n".join(out)


def build_help(reg: "NodeRegistry", topic: str = "") -> str:
    topic = (topic or "").strip()
    specs = reg.all()
    low = topic.lower()

    if not topic or low in _OVERVIEW_ALIASES:
        return _overview(specs)

    if low in _RECIPE_ALIASES:
        head = "## 完整案例（照抄即可，节点 id / 工作流名自己统一改）"
        return "\n\n".join([head] + [_recipe_block(r) for r in _RECIPES])

    names = [*_ACTIONS, *[s.type for s in specs]]
    hit, cand = _match_topic(low, names)
    if not hit:
        if cand:
            return (f"topic「{topic}」匹配到多个：{', '.join(cand)}。"
                    "请写完整名，或不带 topic 看速查总表。")
        known = ", ".join([*names, "recipe"])
        return (f"没有 topic「{topic}」的帮助。可用的 topic：{known}。"
                "不带 topic 可看速查总表。")

    if hit in _ACTIONS:
        parts = [_action_detail(hit)]
        rel = [r for r in _RECIPES if hit in r["actions"]]
        if rel:
            parts.append("相关案例：" + "、".join(r["title"] for r in rel)
                         + "（help topic=recipe 看全文）")
        return "\n".join(parts)

    spec = next(s for s in specs if s.type == hit)
    parts = [_node_detail(spec)]
    rel = [r for r in _RECIPES if hit in r["types"]]
    if rel:
        parts.append("相关案例：" + "、".join(r["title"] for r in rel)
                     + "（help topic=recipe 看全文）")
    return "\n".join(parts)
