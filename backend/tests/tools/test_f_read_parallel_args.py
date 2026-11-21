import asyncio
import importlib
import json
import sys
import types
from pathlib import Path

from app.tools import ToolContext, ToolRegistry


def _load_fs_read():
    builtin_dir = (Path(__file__).resolve().parents[2]
                   / 'app' / 'tools' / 'builtin')
    name = 'app.tools.builtin'
    saved = sys.modules.get(name)
    stub = types.ModuleType(name)
    stub.__path__ = [str(builtin_dir)]
    sys.modules[name] = stub
    try:
        read_mod = importlib.import_module('app.tools.builtin.fs.read')
        schemas_mod = importlib.import_module('app.tools.builtin.fs.schemas')
        return read_mod.f_read, schemas_mod.SCHEMAS['f_read']
    finally:
        if saved is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = saved


_F_READ, _F_READ_SPEC = _load_fs_read()


def _run(tmp_path, args):
    reg = ToolRegistry()
    reg.register('f_read', _F_READ_SPEC['desc'], _F_READ_SPEC['params'],
                 _F_READ, _F_READ_SPEC['required'])
    ctx = ToolContext(str(tmp_path))
    return asyncio.run(reg.execute('f_read', args, ctx))


def _files(tmp_path):
    for name in ('a', 'b', 'c'):
        (tmp_path / f'{name}.txt').write_text(
            '\n'.join(f'{name}{i}' for i in range(1, 11)) + '\n',
            encoding='utf-8')


def _err(result):
    try:
        v = json.loads(result)
        return v.get('error', '') if isinstance(v, dict) else ''
    except (ValueError, TypeError):
        return ''


pass

def test_parallel_paths_lines_align_by_index(tmp_path):
    _files(tmp_path)
    r = _run(tmp_path, {'paths': ['a.txt', 'b.txt', 'c.txt'],
                        'lines': ['1,2', '3,4', '5']})
    assert '===== a.txt [1,2] =====' in r and 'a1\na2' in r
    assert '===== b.txt [3,4] =====' in r and 'b3\nb4' in r
    assert '===== c.txt [5] =====' in r and 'c5' in r
    assert 'a3' not in r and 'b1' not in r and 'c6' not in r


def test_paths_with_string_lines_is_top_level_default(tmp_path):
    _files(tmp_path)
    r = _run(tmp_path, {'paths': ['a.txt', 'b.txt'], 'lines': '1,2'})
    assert 'a1\na2' in r and 'b1\nb2' in r
    assert 'a3' not in r


def test_path_wins_over_paths_alias(tmp_path):
    _files(tmp_path)
    r = _run(tmp_path, {'path': ['a.txt'], 'paths': ['b.txt'],
                        'lines': ['1,2']})
    assert 'a1\na2' in r and 'b1' not in r


def test_length_mismatch_is_rejected(tmp_path):
    _files(tmp_path)
    for args in (
        {'paths': ['a.txt', 'b.txt'], 'lines': ['1,2']},
        {'paths': ['a.txt'], 'lines': ['1,2', '3,4']},
        {'paths': ['a.txt', 'b.txt'], 'lines': []},
    ):
        r = _run(tmp_path, args)
        assert '长度不一致' in _err(r), (args, r)


def test_line_spec_keeps_original_format(tmp_path):
    _files(tmp_path)
    r = _run(tmp_path, {'paths': ['a.txt', 'b.txt', 'c.txt'],
                        'lines': ['1,2', 3, None]})
    assert 'a1\na2' in r
    assert 'b3' in r and 'b4' not in r
    assert 'c1' in r and 'c10' in r
    r2 = _run(tmp_path, {'paths': ['a.txt'], 'lines': ['']})
    assert 'a10' in r2
    r3 = _run(tmp_path, {'paths': ['a.txt'], 'lines': ['-2,']})
    pass
    assert 'a9\na10' in r3 and 'a1' not in r3.splitlines()


def test_bad_line_spec_is_rejected(tmp_path):
    _files(tmp_path)
    for bad in ({'x': 1}, [1, 2], True):
        r = _run(tmp_path, {'paths': ['a.txt'], 'lines': [bad]})
        assert '只能是行区间字符串' in _err(r), (bad, r)


def test_single_path_with_lines_array_is_multi_range(tmp_path):
    _files(tmp_path)
    r = _run(tmp_path, {'path': 'a.txt', 'lines': ['1,2', '5,6']})
    assert 'a1\na2' in r and 'a5\na6' in r
    assert r.count('===== a.txt') == 2
    assert 'a3' not in r


def test_dict_item_own_lines_wins(tmp_path):
    _files(tmp_path)
    r = _run(tmp_path, {'paths': [{'path': 'a.txt', 'lines': '1,2'}, 'b.txt'],
                        'lines': ['3,4', '5,6']})
    assert 'a1\na2' in r and 'a3' not in r
    assert 'b5\nb6' in r


def test_missing_path_reports_clear_error(tmp_path):
    r = _run(tmp_path, {'lines': ['1,2']})
    assert '需要 path' in _err(r)


pass

def test_standard_format_unchanged(tmp_path):
    _files(tmp_path)
    pass
    assert _run(tmp_path, {'path': 'a.txt', 'lines': '1,2'}) == 'a1\na2'
    pass
    r = _run(tmp_path, {'path': 'a.txt'})
    assert r.startswith('a1\n') and 'a10' in r
    pass
    r = _run(tmp_path, {'path': ['a.txt', {'path': 'b.txt', 'lines': '3,4'}]})
    assert '===== a.txt =====' in r and 'a10' in r
    assert '===== b.txt [3,4] =====' in r and 'b3\nb4' in r
    pass
    assert _run(tmp_path, {'path': 'a.txt', 'linenos': True,
                           'lines': '1,2'}) == '1\ta1\n2\ta2'
    meta = json.loads(_run(tmp_path, {'path': 'a.txt', 'info': True}))
    assert meta and 'error' not in meta
    assert _run(tmp_path, {'path': 'a.txt', 'raw': True}) == '\n'.join(
        f'a{i}' for i in range(1, 11))


def test_schema_stays_silent():
    assert 'paths' not in _F_READ_SPEC['params']
    assert _F_READ_SPEC['params']['lines']['type'] == 'string'
    assert _F_READ_SPEC['required'] == ['path']


def test_positional_call_still_works(tmp_path):
    _files(tmp_path)
    ctx = ToolContext(str(tmp_path))
    assert _F_READ('a.txt', ctx, lines='1,2') == 'a1\na2'
    assert _F_READ('a.txt', ctx) == '\n'.join(f'a{i}' for i in range(1, 11))
