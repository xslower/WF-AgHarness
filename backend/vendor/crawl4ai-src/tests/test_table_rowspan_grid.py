
import time

from lxml import html as lhtml

from crawl4ai import DefaultTableExtraction


def _extract(html: str):
    pass
    return DefaultTableExtraction().extract_tables(lhtml.fromstring(f"<div>{html}</div>"))


def test_th_row_headers_in_body_are_kept():
    tables = _extract("""
    <table>
    <tr><th></th><th>Feature A</th><th>Feature B</th></tr>
    <tr><th scope="row">Item 1</th><td>yes</td><td>yes</td></tr>
    <tr><th scope="row">Item 2</th><td>no</td><td>yes</td></tr>
    </table>""")
    assert len(tables) == 1
    assert tables[0]["headers"] == ["", "Feature A", "Feature B"]
    assert tables[0]["rows"] == [["Item 1", "yes", "yes"], ["Item 2", "no", "yes"]]


def test_rowspan_value_repeats_into_covered_rows():
    tables = _extract("""
    <table>
    <thead><tr><th>Group</th><th>Option X</th><th>Option Y</th></tr></thead>
    <tbody>
    <tr><td rowspan="2">Group 1</td><td>value x</td><td>value y</td></tr>
    <tr><td colspan="2">note that applies to X and Y</td></tr>
    </tbody></table>""")
    assert len(tables) == 1
    assert tables[0]["headers"] == ["Group", "Option X", "Option Y"]
    assert tables[0]["rows"] == [
        ["Group 1", "value x", "value y"],
        ["Group 1", "note that applies to X and Y", "note that applies to X and Y"],
    ]


def test_rowspan_does_not_leak_past_a_short_row():
    tables = _extract("""
    <table>
    <thead><tr><th>H1</th><th>H2</th><th>H3</th></tr></thead>
    <tbody>
    <tr><td>a</td><td>b</td><td rowspan="2">SPAN</td></tr>
    <tr><td>c</td></tr>
    <tr><td>x</td><td>y</td><td>z</td></tr>
    </tbody></table>""")
    assert tables[0]["rows"] == [
        ["a", "b", "SPAN"],
        ["c", "", "SPAN"],
        ["x", "y", "z"],
    ]


def test_rowspan_and_colspan_on_the_same_cell():
    tables = _extract("""
    <table>
    <thead><tr><th>A</th><th>B</th><th>C</th><th>D</th></tr></thead>
    <tbody>
    <tr><td rowspan="2" colspan="2">BIG</td><td>c1</td><td>d1</td></tr>
    <tr><td>c2</td><td>d2</td></tr>
    </tbody></table>""")
    assert tables[0]["rows"] == [
        ["BIG", "BIG", "c1", "d1"],
        ["BIG", "BIG", "c2", "d2"],
    ]


def test_rowspan_reaching_past_the_last_row_is_clamped():
    tables = _extract("""
    <table>
    <thead><tr><th>A</th><th>B</th></tr></thead>
    <tbody>
    <tr><td rowspan="9">X</td><td>b1</td></tr>
    <tr><td>b2</td></tr>
    </tbody></table>""")
    assert tables[0]["rows"] == [["X", "b1"], ["X", "b2"]]


def test_plain_table_without_spans_is_unchanged():
    tables = _extract("""
    <table>
    <thead><tr><th>Name</th><th>Qty</th><th>Price</th></tr></thead>
    <tbody>
    <tr><td>Widget</td><td>2</td><td>10</td></tr>
    <tr><td>Gadget</td><td>5</td><td>25</td></tr>
    </tbody></table>""")
    assert tables[0]["headers"] == ["Name", "Qty", "Price"]
    assert tables[0]["rows"] == [["Widget", "2", "10"], ["Gadget", "5", "25"]]


def test_key_value_first_row_is_not_mistaken_for_a_header():
    tables = _extract("""
    <table>
    <tr><th scope="row">Food</th><td>Apple pie</td></tr>
    <tr><th scope="row">Drink</th><td>Apple cider</td></tr>
    </table>""")
    assert tables[0]["rows"] == [["Food", "Apple pie"], ["Drink", "Apple cider"]]


def test_absurd_spans_are_clamped_instead_of_exploding():
    html = """
    <table>
    <thead><tr><th>A</th><th>B</th></tr></thead>
    <tbody>
    <tr><td rowspan="1000000" colspan="1000000">X</td><td>b1</td></tr>
    <tr><td>c1</td><td>c2</td></tr>
    </tbody></table>"""
    started = time.perf_counter()
    tables = _extract(html)
    elapsed = time.perf_counter() - started

    assert elapsed < 2, f"clamping regressed: took {elapsed:.1f}s"
    rows = tables[0]["rows"]
    assert len(rows) == 2, "rowspan must not invent rows beyond the table"
    limit = DefaultTableExtraction.COLSPAN_LIMIT
    assert all(len(row) <= limit for row in rows), "colspan must be capped"


def test_invalid_span_attribute_counts_as_one():
    tables = _extract("""
    <table>
    <thead><tr><th>A</th><th>B</th></tr></thead>
    <tbody>
    <tr><td colspan="100%">a</td><td>b</td></tr>
    <tr><td rowspan="lots">c</td><td>d</td></tr>
    <tr><td colspan="-3">e</td><td>f</td></tr>
    </tbody></table>""")
    assert tables[0]["rows"] == [["a", "b"], ["c", "d"], ["e", "f"]]
