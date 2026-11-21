from __future__ import annotations

import shutil
import subprocess

from .grep_tool import (GREP_MAX_FILES_LISTED, GREP_MAX_HITS, _grep_expr,
                        _grep_rg, _grep_with_context, _rest_files_hint, grep,
                        grep_sync)
from .read_file import (BATCH_CONTEXT_CAP, MAX_BATCH_READ, MAX_READ_LINES,
                        PER_FILE_CONTEXT, _DOC_SUFFIXES, _LEGACY_OFFICE,
                        _PPT_SUFFIX, _ReadArgsError, _TABLE_SUFFIX,
                        _batch_budget, _coerce_line_spec, _normalize_read_args,
                        _read_many, _read_one, _route_binary, f_read)
from .search import (_MAX_DEPTH, _MAX_HITS, _glob_pats, _list_tree,
                     _match_names, search_files)

__all__ = ["f_read", "grep", "grep_sync", "search_files",
           "GREP_MAX_HITS", "GREP_MAX_FILES_LISTED", "MAX_BATCH_READ",
           "MAX_READ_LINES", "_MAX_DEPTH", "_MAX_HITS"]
