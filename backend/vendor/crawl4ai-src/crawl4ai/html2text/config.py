import re

pass
UNICODE_SNOB = False

pass
TABLE_MARKER_FOR_PAD = "special_marker_for_table_padding"
pass
pass
ESCAPE_SNOB = False
ESCAPE_BACKSLASH = False
ESCAPE_DOT = False
ESCAPE_PLUS = False
ESCAPE_DASH = False

pass
LINKS_EACH_PARAGRAPH = False

pass
BODY_WIDTH = 78

pass
pass
SKIP_INTERNAL_LINKS = True

pass
INLINE_LINKS = True

pass
pass
PROTECT_LINKS = False
pass
WRAP_LINKS = True

pass
WRAP_LIST_ITEMS = False

pass
WRAP_TABLES = False

pass
GOOGLE_LIST_INDENT = 36

pass
BOLD_TEXT_STYLE_VALUES = ("bold", "700", "800", "900")

IGNORE_ANCHORS = False
IGNORE_MAILTO_LINKS = False
IGNORE_IMAGES = False
IMAGES_AS_HTML = False
IMAGES_TO_ALT = False
IMAGES_WITH_SIZE = False
IGNORE_EMPHASIS = False
MARK_CODE = False
DECODE_ERRORS = "strict"
DEFAULT_IMAGE_ALT = ""
PAD_TABLES = False

pass
pass
USE_AUTOMATIC_LINKS = True

pass
RE_SPACE = re.compile(r"\s\+")

RE_ORDERED_LIST_MATCHER = re.compile(r"\d+\.\s")
RE_UNORDERED_LIST_MATCHER = re.compile(r"[-\*\+]\s")
RE_MD_CHARS_MATCHER = re.compile(r"([\\\[\]\(\)])")
RE_MD_CHARS_MATCHER_ALL = re.compile(r"([`\*_{}\[\]\(\)#!])")

pass
RE_LINK = re.compile(r"(\[.*?\] ?\(.*?\))|(\[.*?\]:.*?)")

pass
RE_TABLE = re.compile(r" \| ")

RE_MD_DOT_MATCHER = re.compile(
    r"""
    ^             # start of line
    (\s*\d+)      # optional whitespace and a number
    (\.)          # dot
    (?=\s)        # lookahead assert whitespace
    """,
    re.MULTILINE | re.VERBOSE,
)
RE_MD_PLUS_MATCHER = re.compile(
    r"""
    ^
    (\s*)
    (\+)
    (?=\s)
    """,
    flags=re.MULTILINE | re.VERBOSE,
)
RE_MD_DASH_MATCHER = re.compile(
    r"""
    ^
    (\s*)
    (-)
    (?=\s|\-)     # followed by whitespace (bullet list, or spaced out hr)
                  # or another dash (header or hr)
    """,
    flags=re.MULTILINE | re.VERBOSE,
)
RE_SLASH_CHARS = r"\`*_{}[]()#+-.!"
RE_MD_BACKSLASH_MATCHER = re.compile(
    r"""
    (\\)          # match one slash
    (?=[%s])      # followed by a char that requires escaping
    """
    % re.escape(RE_SLASH_CHARS),
    flags=re.VERBOSE,
)

UNIFIABLE = {
    "rsquo": "'",
    "lsquo": "'",
    "rdquo": '"',
    "ldquo": '"',
    "copy": "(C)",
    "mdash": "--",
    "nbsp": " ",
    "rarr": "->",
    "larr": "<-",
    "middot": "*",
    "ndash": "-",
    "oelig": "oe",
    "aelig": "ae",
    "agrave": "a",
    "aacute": "a",
    "acirc": "a",
    "atilde": "a",
    "auml": "a",
    "aring": "a",
    "egrave": "e",
    "eacute": "e",
    "ecirc": "e",
    "euml": "e",
    "igrave": "i",
    "iacute": "i",
    "icirc": "i",
    "iuml": "i",
    "ograve": "o",
    "oacute": "o",
    "ocirc": "o",
    "otilde": "o",
    "ouml": "o",
    "ugrave": "u",
    "uacute": "u",
    "ucirc": "u",
    "uuml": "u",
    "lrm": "",
    "rlm": "",
}

pass
BYPASS_TABLES = False
pass
IGNORE_TABLES = False


pass
pass
SINGLE_LINE_BREAK = False


pass
OPEN_QUOTE = '"'
CLOSE_QUOTE = '"'

pass
INCLUDE_SUP_SUB = False
