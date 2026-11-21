from __future__ import annotations

from typing import TYPE_CHECKING

from .config_write import config_write
from .paths import f_path, trash_tool
from .read import f_read, grep, search_files
from .write import f_replace, f_write

if TYPE_CHECKING:
    from ... import ToolRegistry

pass
pass
pass
pass
pass
pass
pass
pass
SCHEMAS: dict[str, dict] = {
    "f_read": {
        "desc": (
            "读文本文件，默认**不带行号**（多数场景行号对模型是噪声）；"
            "要按行号定位/引用时给 linenos=true，正文每行加 1 基行号 + Tab 前缀"
            "（与 f_write 的 lines 同一口径）。\n"
            "**path 可以传数组一次读多个文件（最多 8 个）**：[\"a.py\", \"b.py\"] 或 "
            "[{\"path\": \"a.py\", \"lines\": \"1,80\"}, {\"path\": \"b.py\", \"lines\": \"-20,\"}]，"
            "一次工具调用拿回全部，别一个个读。超过 8 个**不报错**：先读前 8 个，"
            "尾部列出未读路径，再发一次 f_read 补齐即可（不用重读已给过的）。\n"
            "批量读的结果长度按文件数自动放宽，每段单独留头尾，中间文件不会被切没。\n"
            "**找某功能的相关片段时，优先 spawn subagent**：让它用检索/读取工具定位后"
            "只回「片段原文 + 前后 3 行上下文 + 路径:行号」，别把大范围阅读结果留在主会话。\n"
            "**长文件先给大纲**：不给 lines 且文件很长（≥200 行）时只返回索引 —— "
            "代码给方法/类签名+注释+行号范围，md 给标题+行号，不含全文；"
            "即使给了 mode=\"full\" 也先给大纲（全文会灌进上下文、每轮重发）。"
            "大纲是独立的前置索引（自带行号范围），不受 linenos 影响。"
            "看清索引后用 lines=\"A,B\" 取要改的区间原文（可与数组一次取多段）；"
            "确实要整篇全文给 lines=\"1,\"。\n"
            "info=true 时不读内容，只返回大小/权限/修改时间/行数等路径元信息（目录也可以查）。\n"
            "**图片（png/jpg/jpeg/webp/gif/bmp）直接读**：返回一句「图已读取」，"
            "图本身会紧随本批工具结果作为一条用户消息给出 —— 能看图的模型直接看图，"
            "否则自动附一段视觉模型的文字转述。需要看图 debug 时（界面/图表/报错截图）"
            "直接用 f_read 读，不要去调 ocr（那是只抠文字）。\n"
            "**lines** 选要看的区间（1 基，含端点；负数从末尾倒数）：\n"
            "· 不给 → 全文（最多 2000 行）\n"
            "· \"N\" → 第 N 行\n"
            "· \"A,B\" → 第 A~B 行\n"
            "· \"A,\" → 第 A 行到文件末尾（等价 \"A,-1\"）\n"
            "· \"-3,\" → 末尾 3 行（\"-1,\" = 最后一行；\"-2,-1\" = 倒数第 2 行到最后一行）\n"
        ),
        "params": {"path": {
            "type": ["string", "array"],
            "description": "单个路径，或多个路径的数组（元素可为路径字符串，"
                           "或 {\"path\": ..., \"lines\": ...} 自带区间）"},
         "lines": {"type": "string",
                   "description": "要读的行区间（1 基，含端点）：\"N\" / \"A,B\" / "
                                  "\"A,\" / \"-3,\"（末尾 3 行）；不给=全文"},
         "mode": {"type": "string",
                  "description": "\"outline\"=只要大纲索引；\"full\"=强制全文；"
                                 "不给=长文件自动大纲、短文件全文"},
         "linenos": {"type": "boolean",
                     "description": "正文每行是否带 1 基行号前缀（默认 false，不带）。"
                                    "只管正文，大纲与超长截断都不受它影响；"
                                    "要按行号 f_write 编辑或引用 路径:行号 时才传 true"}},
        "fn": f_read,
        "required": ['path'],
    },
    "f_write": {
        "desc": (
            "写文件。**一次要改多处就传 edits 数组**（半强迫一次给全，别一轮改一处）：\n"
            "edits=[{before,after,replace,append,expect,content}, ...]，\n"
            "每项都用**全部落点参数**，落点由参数名决定（行号 1 基，与 f_read 一致）：\n"
            "· before=N → 第 N 行**之前**插入；after=N → 第 N 行**之后**插入\n"
            "· replace=\"A,B\" → 把第 A~B 行（含端点）替换成 content；\"A,\" = A 行到末尾\n"
            "· append=true → 追加到文件末尾（「追加」只有这一条路）\n"
            "· 都不给 → 整篇覆盖（content = 文件全文，父目录自动创建）\n"
            "**负数一律是从末尾倒数的行号**（-1 = 最后一行）：before=-1 = 最后一行之前，"
            "after=-1 = 最后一行之后。\n"
            "**expect**（可配 before/after/replace）：内容锚点，给一段原文即可，"
            "**可以多行**（与 f_replace 的 old 同一套匹配：逐行 trim、忽略空行、"
            "必须连续）：命中且偏差 ≤1 行（全文件唯一命中时 ≤3 行）→ 自动按"
            "命中行执行并说明偏差；超出容差或找不到 → 拒绝并回显实际位置。\n"
            "**批量行号按原始文件算**：系统会从后往前应用，前面的插入不会让后面的"
            "行号漂移，不必自己算偏移。若两处区间重叠（如 2,4 与 3,5）、或整篇覆盖"
            "与其它改动混在一批，**整批拒绝、一处都不写**，请合并或分开调用。\n"
            "**mode / truncate_ok 在数组外、整批共用一个值**：mode 1=执行（默认）"
            "/2=撤销本会话内该文件的上一次写入/3=先回滚到上一次写入前的内容再按本次"
            "参数重写（后两个批量只做一次，与 f_replace 共用同一回退栈）；"
            "truncate_ok=true 才允许把长文件整体换成极短内容（防误覆盖；追加请用 append=true）。\n"
            "写 .py 会自动校验语法：缩进错自动修，**合法重构一律放行**（删函数、改名、"
            "改签名、整篇重写都不拦）。改完不合法时按写入量分档：≤2 行 → 拒绝（大概率是"
            "改错了地方）；≥3 行 → 照写但回显警告当前文件不合法，可接着改或用 mode=3 回滚重写。\n"
        ),
        "params": {"path": {"type": "string", "description": "文件路径（数组外，一批改同一个文件）"},
         "edits": {"type": "array",
                   "description": "一次要改的多处。每项含 content 与落点参数"
                                  "（before/after/replace/append/expect）；"
                                  "mode 与 truncate_ok 不在这里，整批共用",
                   "items": {"type": "object"}},
         "content": {"type": "string", "description": "单处旧用法：要写入的文本"},
         "before": {"type": "integer",
                    "description": "单处旧用法：在第 N 行之前插入（负数=倒数）"},
         "after": {"type": "integer",
                   "description": "单处旧用法：在第 N 行之后插入（负数=倒数）"},
         "replace": {"type": "string",
                     "description": "单处旧用法：替换区间 \"A,B\" / \"A,\""},
         "expect": {"type": "string",
                    "description": "单处旧用法：内容锚点，该行（可多行原文）必须能匹配到"},
         "append": {"type": "boolean", "description": "单处旧用法：true=追加到文件末尾"},
         "mode": {"type": "integer",
                  "description": "整批共用：1=执行（默认），2=撤销上一次写入，"
                                 "3=回滚到上一次写入前再按本次参数重写"},
         "truncate_ok": {"type": "boolean",
                         "description": "整篇覆盖时把长文件换成极短内容必须显式设 true"}},
        "fn": f_write,
        "required": ['path', 'edits'],
    },
    "f_replace": {
        "desc": (
            "按内容替换文件里的文本。**一次要改多处就传 edits 数组**（别一轮改一处）：\n"
            "edits=[{old, new, replace_count}, ...]。\n"
            "old 按**字面量**匹配（不做正则），可多行 = 整块替换。定位与 f_write 的"
            "expect **同一套**：切行 → 每行 trim → 去掉空行 → 在非空行序列上找连续一段"
            "（文件里的空行不打断连续，old 的 A\\nB 能匹配 A/空行/B）。old 单行还能"
            "只改行中片段（改 `x = foo(bar)` 里的 foo）。new 为空串 = 删除这段。\n"
            "old 出现多次且没传 replace_all / replace_count → 报错并列出所有出现位置"
            "（不擅自全改）；一处都没找到 → 报错并给出文件里最接近的几行。\n"
            "**replace_count=N**：只替换前 N 处（按文件顺序），其余保留；"
            "0/不传 = 沿用 replace_all 的旧行为。批量里逐处基于当前文件匹配。\n"
            "**mode 在数组外、整批共用**：1=执行（默认）；2=撤销上一次写入；\n"
            "3=先回滚到上一次写入前的内容再按本次参数重写（批量只做一次）。\n"
            "改完不合法时同样按写入量分档（≤2 行拒绝、≥3 行写入并警告）。\n"
            "单处改动仍可用旧的扁平参数（old/new/replace_all）。"
        ),
        "params": {"path": {"type": "string", "description": "文件路径（数组外）"},
         "edits": {"type": "array",
                   "description": "一次要改的多处。每项含 old/new/replace_count；"
                                  "mode 不在这里，整批共用",
                   "items": {"type": "object"}},
         "old": {"type": "string", "description": "单处旧用法：要被替换的原文"},
         "new": {"type": "string", "description": "单处旧用法：替换成的内容；空串=删除"},
         "mode": {"type": "integer",
                  "description": "整批共用：1=执行（默认），2=撤销上一次写入，"
                                 "3=回滚到上一次写入前再按本次参数重写"},
         "replace_all": {"type": "boolean",
                         "description": "单处旧用法：true=替换所有出现位置"},
         "replace_count": {"type": "integer",
                           "description": "单处旧用法：只替换前 N 处（0=不限）"}},
        "fn": f_replace,
        "required": ['path', 'edits'],
    },
    "search_files": {
        "desc": (
            "找文件/看目录。传 pattern=按 glob 匹配文件名（如 *.py、src/**/*.ts）；"
            "不传 pattern=列出目录树（**真 3 层**，depth 默认 3、硬顶 3）。\n"
            "列树时每展开一个目录先探条目数：超多的目录（临时/缓存/产物）整组换成\n"
            "「[N 项，未展开；需要再看请 search_files(path=\"...\", depth=2)]」，"
            "一个单文件都不列，防止几万文件灌进上下文。输出超长也从最深层目录"
            "整组折叠、保住上层目录框架 —— 不会只列一半文件让你误判目录内容。\n"
            "隐藏 . 开头 / node_modules / dist 等无关目录由系统自动跳过，不用自己排除。\n"
            "折叠行带 path，觉得有必要就用它再查一次即可。"
        ),
        "params": {"path": {"type": "string", "description": "起始目录（相对路径锚在项目目录），默认项目目录"},
         "pattern": {"type": "string", "description": "glob 模式，空=列目录树"},
         "depth": {"type": "integer", "description": "列目录时的展开层数，默认 3、硬顶 3"}},
        "fn": search_files,
        "required": [],
    },
    "grep": {
        "desc": (
            "搜索文件内容（默认带命中行前后各 3 行上下文，等于 grep -C 3；"
            "通常一次就够看清，不必再 f_read 取上下文）。\n"
            "**key 是关键词数组，支持多 key**：key=['foo', 'bar'] 一次搜多个词，"
            "**任一命中即返回**（OR 语义），不用拼正则、不用多次调用。\n"
            "regex=false（默认）= 按字面量匹配，关键词里的 . * ( ) 等不具特殊含义；"
            "regex=true = 每个 key 是一条正则表达式（如 ['^class ', 'TODO.*']）。\n"
            "path 是单个目录、include 是单个 glob；大范围搜完只取相关片段"
            "（或派 subagent 只回片段+路径:行号），别把全量结果留在主上下文。\n"
            "**outline=true = 查方法级代码地图**：不读全文，按 key 返回「文件路径 + "
            "类/方法签名 + 行号范围」，用于「某功能在哪些方法里」的定位；key 留空给"
            "项目文件概览。索引覆盖 .py/.ts/.tsx/.js/.jsx/.md，结果靠缩进展示层级"
            "（类/接口顶格、成员缩进两层），只在 path 范围内查。拿到路径:行号再用 "
            "f_read(lines=) 取原文。要读某片功能区代码时先查一次地图，能省掉多轮"
            "列目录/猜文件/读大纲。"
        ),
        "params": {"key": {"type": "array", "items": {"type": "string"},
                   "description": "关键词数组，支持多个；任一命中即返回（OR）"},
         "regex": {"type": "boolean",
                   "description": "true=每个 key 按正则匹配；false/不传=按字面量匹配"},
         "path": {"type": "string", "description": "搜索起始目录（相对路径锚在项目目录），默认项目目录"},
         "include": {"type": "string", "description": "文件名 glob 过滤，默认 *"},
         "context": {"type": "integer",
                     "description": "命中行前后各带几行上下文（默认 3；传 0 才不带）"},
         "outline": {"type": "boolean",
                     "description": "true=查方法级代码地图（只在 path 范围内按 key 返回文件+签名+行号范围，不读全文）；默认 false=正文检索"}},
        "fn": grep,
        "required": ['key'],
    },
    "f_path": {
        "desc": (
            "路径操作（创建/移动/复制/删除）。action 决定动作："
            "create=新建文件或目录（不覆盖已有）；move=移动或重命名；copy=复制；"
            "delete=删除（目录递归）——默认移入项目内回收站 .trash 可恢复，"
            "仅在设置里关闭回收站时才是真删，且只允许删除项目目录内的路径。"
            "move/copy 需要 dest。"
        ),
        "params": {"action": {"type": "string", "enum": ["create", "move", "copy", "delete"],
                    "description": "要做的操作"},
         "path": {"type": "string", "description": "目标路径（源路径）；相对路径锚在项目目录"},
         "dest": {"type": "string", "description": "move/copy 的目标路径；相对路径锚在项目目录"},
         "is_dir": {"type": "boolean", "description": "create 时 true=建目录"},
         "content": {"type": "string", "description": "create 文件时的初始内容"}},
        "fn": f_path,
        "required": ['action', 'path'],
    },
    "config_write": {
        "desc": (
            "改**结构化数据文件**（json / jsonl / yaml / ini）—— 只给路径和值，"
            "序列化、缩进、引号、转义全由工具做。**代码/文本/大段 markdown 仍用 "
            "f_write；只要目标文件是这四种格式，就用本工具。**\n"
            "为什么：用 f_write 写 json 是「字符串里再装 JSON」，引号要转两层，"
            "错一个反斜杠整份坏掉；YAML 还得自己判什么时候该加引号（yes/on/01/#）——\n"
            "这类错误不报错、只默默改值。本工具把值当**结构**传，只有一层转义。\n"
            "**ops 一次给全（别一轮一处）**，按顺序改同一份内容，任一步失败整批不写：\n"
            "· {\"op\":\"set\",\"path\":\"a.b[0].c\",\"value\":<任意 JSON 值>} —— 存在就改、不存在就建\n"
            "· {\"op\":\"delete\",\"path\":\"a.b\"} —— 删键/下标（不存在会报错并列出相近键）\n"
            "· {\"op\":\"merge\",\"path\":\"a\",\"value\":{...}} —— 深合并，只覆盖给出的键（列表整体替换）\n"
            "· {\"op\":\"append\",\"path\":\"a.list\",\"value\":<任意>} —— 往列表末尾追加\n"
            "· {\"op\":\"replace\",\"value\":<整个文档>} —— 整份替换（不接受 path）\n"
            "**path**：`a.b[0].c` 与 `a.b.0.c` 等价；数字段在列表上是下标、在 dict 上是键；"
            "键名带点/方括号时用引号 `a.\"b.c\".d`；不传（或空）= 根。\n"
            "**value 直接给结构本身**（对象就传对象），不要传字符串化 JSON —— 万一把"
            "`{\"a\":1}` 当字符串传了，工具会自动按结构写入并在回显里说明；确实想存"
            "这段字符串时给该项加 `as_string: true`。\n"
            "**format** 默认按后缀判（.json/.jsonl/.ndjson/.yaml/.yml/.ini/.cfg/.conf），"
            "后缀不对时才显式传 format。\n"
            "**会保留原文件风格**：JSON 的缩进宽度、`\\uXXXX` 习惯、键序、CRLF 与末尾换行；"
            "YAML 的注释/锚点/引号风格（ruamel round-trip）；INI 是行级外科编辑，注释、"
            "空行、键的大小写和分隔符空格都不动（**但 INI 值是字符串**，数值也会写成文本）。\n"
            "**INI 限制**：path 只支持两级 `section.key`；只支持 set/delete；已存在的文件"
            "不允许 op=replace（会洗掉注释）。\n"
            "**写前自检**：落盘前会把结果重新解析一遍，读不回预期值就拒绝写入并说明原因。\n"
            "mode：1=执行（默认）/2=撤销本会话内该文件上一次写入/3=回滚后重写（与 f_write "
            "共用同一回退栈）。op=replace 且新内容大幅缩水时需要 `truncate_ok: true`。\n"
        ),
        "params": {
            "path": {"type": "string", "description": "目标文件路径（相对路径锚项目目录）"},
            "ops": {"type": "array",
                    "description": "要做的改动（按顺序、原子）；每项含 op / path / value，"
                                   "可另加 as_string=true 禁止值纠偏",
                    "items": {"type": "object"}},
            "format": {"type": "string",
                       "enum": ["json", "jsonl", "yaml", "ini"],
                       "description": "显式指定格式；不给就按后缀判"},
            "mode": {"type": "integer",
                     "description": "1=执行（默认），2=撤销上一次写入，3=回滚后重写"},
            "truncate_ok": {"type": "boolean",
                            "description": "op=replace 把大文件换成极短内容时必须显式设 true"}},
        "fn": config_write,
        "required": ['path', 'ops'],
    },
    "trash": {
        "desc": (
            "回收站：list=查看当前项目回收站的批次/文件数/占用（给 stamp 则列出该批次内的条目）；"
            "purge=清理（days=0 全部清空，days=N 只清 N 天前的批次）；"
            "restore=把回收站里的一项恢复到项目内（path=相对 `.trash/` 的条目路径，"
            "形如 `bin/sub/a.txt.20261029-231027`；不带版本号则恢复该路径最新一版。"
            "可选 to=恢复到项目内指定位置；目标已存在时自动加序号，绝不覆盖）。"
            "只有确实要腾磁盘时用 purge，普通删除已经自动进回收站。"
        ),
        "params": {"action": {"type": "string",
                              "enum": ["list", "purge", "restore"],
                              "description": "list 查看 / purge 清理 / restore 恢复"},
         "days": {"type": "integer",
                  "description": "purge 保留天数：0=全清（默认），N=只清 N 天前"},
         "stamp": {"type": "string",
                   "description": "list 时指定批次（形如 20261029-231027），用于查看该批次条目"},
         "path": {"type": "string",
                  "description": "restore 要恢复的条目（相对项目根的回收站内路径）"},
         "to": {"type": "string",
                "description": "restore 恢复目标（项目内路径，默认回原位置）"}},
        "fn": trash_tool,
        "required": ['action'],
    },
}
