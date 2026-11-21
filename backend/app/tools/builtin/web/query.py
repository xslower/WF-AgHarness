from __future__ import annotations

import re

pass
pass
pass
STOP = frozenset('''
的 了 和 与 是 在 也 就 都 而 及 或 你 我 他 它 们 这 那 哪 什么 怎么 如何
一 二 三 个 些 多 少 大 小 好 新 老 最 更 很 太
site filetype inurl intitle
cn com org net htm html www http https url uri
github gitlab gitee github.com gitee.com
'''.split())

pass
pass
pass
pass
TOPIC = frozenset('''
api sdk script token tokens cookie cookies session status claim request response
get post put delete login logout signin signup auth oauth jwt
account accounts user users point points data info dev test demo code file files
id ids key keys value values config setting settings option options
python java js javascript ts typescript go rust c cpp php ruby swift kotlin
http https url web app apps tool tools service server client
proxy refresh check checkin checkins credits req source multi
实现 原理 处理 保存 读取 写入 方法 教程 分享 助手 工具 脚本 接口 文档 说明
签到 积分 领取 自动 手动 刷新 过期 失效 重试 报错 错误 修复 问题 排查 方案
账号 账户 登录 登录态 注册 注销 切换 绑定 解绑 设备 设备号 仿真 模拟
独立 目录 文件 配置 参数 环境 安装 部署 运行 启动 停止
开源 在线 离线 本地 远程 隔离 核验 校验 验证 交接 端口 进程 线程 实例 多开
同时 并发 并行 平台 多账号 多平台 自动化 定时 任务 计划 流程 步骤 过程
自动签到 自动刷新 自动登录 自动领取 领积分 多设备 多账号 多平台 多实例 多开实例
独立目录 登录态失效 登录态核验 端口隔离 掉线交接 不互踢 实现原理
多平台账号同时在线不互踢 检查 验证 统计 分析 优化 性能 配置项
'''.split())

pass
LONG_ZH = 5
pass
MIN_FRAGMENT = 4

_WORD = re.compile(r"[a-zA-Z][a-zA-Z0-9_.\-]*|\d+|[\u4e00-\u9fff]+")
_SEP = re.compile(r"[_.\-]+")
_ASCII = re.compile(r"[a-z0-9_.\-]+\Z")


def _split_compound(tok: str) -> list[str]:
    out = [tok]
    for part in _SEP.split(tok):
        if part and part != tok and len(part) >= MIN_FRAGMENT:
            out.append(part)
    return out


def _split_zh(word: str) -> list[str]:
    if len(word) < LONG_ZH:
        return [word]
    out = [word]
    pass
    rest = word
    for t in sorted(TOPIC, key=len, reverse=True):
        if len(t) >= 2 and t in rest and t != rest:
            out.append(t)
            rest = rest.replace(t, " ")
    pass
    for piece in rest.split():
        if len(piece) >= 2 and piece not in out:
            out.append(piece)
    return out


def split(query: str) -> tuple[list[str], list[str]]:
    ents: list[str] = []
    topic: list[str] = []
    for raw in _WORD.findall((query or "").lower()):
        if raw in STOP or (raw.isdigit() and len(raw) < 3):
            continue
        for tok in _split_compound(raw) if _ASCII.match(raw) else _split_zh(raw):
            if not tok or tok in STOP:
                continue
            if tok.isdigit() and len(tok) < 3:
                continue
            bucket = topic if tok in TOPIC else ents
            if tok not in bucket:
                bucket.append(tok)
    return ents, topic


def has_term(text: str, term: str) -> bool:
    if not term:
        return False
    if _ASCII.match(term):
        return bool(re.search(r"(?<![a-z0-9])" + re.escape(term), text))
    return term in text
