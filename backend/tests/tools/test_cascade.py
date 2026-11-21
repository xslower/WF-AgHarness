from __future__ import annotations

import asyncio
import json

import pytest

from app.tools import cascade


@pytest.fixture(autouse=True)
def _clean():
    cascade.reset()
    yield
    cascade.reset()


def test_is_failure_only_for_error_objects():
    assert cascade.is_failure('{"error": "x"}') is True
    assert cascade.is_failure('{"ok": false, "error": "x"}') is True
    assert cascade.is_failure('{"ok": true, "text": "x"}') is False
    assert cascade.is_failure('{"error": ""}') is False
    pass
    assert cascade.is_failure('结果如下 {"error": "x"}') is False
    assert cascade.is_failure('') is False


def test_only_four_capabilities_and_aliases():
    for cap in ('web', 'asr', 'ocr', 'gen_image', 'embed'):
        cascade.register(cap, 'p', lambda **k: 'ok')
    assert cascade.normalize('generate_image') == 'gen_image'
    assert cascade.normalize('transcribe_audio') == 'asr'
    assert cascade.normalize('embedding') == 'embed'
    with pytest.raises(ValueError):
        cascade.register('run_command', 'p', lambda **k: 'ok')


def test_system_first_then_plugin_fallback():
    calls = []

    async def plugin(**kwargs):
        calls.append('plugin')
        return 'paid-result'

    cascade.register('web', 'paid', plugin, order='after')

    async def system():
        calls.append('system')
        return '{"error": "免费搜索失败"}'

    out = asyncio.run(cascade.run('web', {'query': 'q', 'limit': 5}, None, system))
    assert out == 'paid-result'
    assert calls == ['system', 'plugin']


def test_system_success_does_not_call_plugin():
    calls = []

    async def plugin(**kwargs):
        calls.append('plugin')
        return 'paid-result'

    cascade.register('web', 'paid', plugin, order='after')

    async def system():
        calls.append('system')
        return '[1] 免费结果'

    out = asyncio.run(cascade.run('web', {'query': 'q'}, None, system))
    assert out == '[1] 免费结果'
    assert calls == ['system']


def test_plugin_first_then_system_fallback():
    calls = []

    async def plugin(**kwargs):
        calls.append('plugin')
        return '{"error": "没配置 key"}'

    cascade.register('web', 'paid', plugin, order='before')

    async def system():
        calls.append('system')
        return '[1] 免费结果'

    out = asyncio.run(cascade.run('web', {'query': 'q'}, None, system))
    assert out == '[1] 免费结果'
    assert calls == ['plugin', 'system']


def test_plugin_exception_falls_back_and_args_are_filtered():
    seen = {}

    async def plugin(query='', ctx=None):
        seen['query'] = query
        seen['has_ctx'] = ctx is not None
        raise RuntimeError('boom')

    pass
    cascade.register('web', 'paid', plugin, order='before')

    async def system():
        return 'free'

    out = asyncio.run(cascade.run('web', {'query': 'q', 'limit': 5}, 'CTX', system))
    assert out == 'free'
    pass
    assert seen == {'query': 'q', 'has_ctx': True}


def test_no_plugin_just_runs_system():
    async def system():
        return 'free'

    assert asyncio.run(cascade.run('asr', {'file_path': 'a'}, None, system)) == 'free'
