
import pytest

pypdf = pytest.importorskip("pypdf")

from crawl4ai.processors.pdf.processor import NaivePDFProcessorStrategy

N_PAGES = 12
BATCH_SIZE = 4
TITLE_CASE_LINE = "Assessment Overview"


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _page_lines(page_number: int):
    return [
        f"Chapter Heading Number {page_number}",
        TITLE_CASE_LINE,
        f"this is the body of page {page_number}. " * 20,
    ]


def _build_pdf(path, n_pages: int = N_PAGES) -> None:
    objects = []
    kids = " ".join(f"{3 + 3 * i} 0 R" for i in range(n_pages))
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>")
    for i in range(n_pages):
        page_obj = 3 + 3 * i
        content_obj = page_obj + 1
        font_obj = page_obj + 2
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_obj} 0 R "
            f"/Resources << /Font << /F1 {font_obj} 0 R >> >> >>"
        )
        stream_lines = ["BT /F1 12 Tf 72 720 Td"]
        for j, line in enumerate(_page_lines(i + 1)):
            if j:
                stream_lines.append("0 -16 Td")
            stream_lines.append(f"({_escape_pdf_text(line)}) Tj")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines).encode("latin-1")
        objects.append((f"<< /Length {len(stream)} >>\nstream\n", stream, "\nendstream"))
        objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{idx} 0 obj\n".encode("latin-1")
        if isinstance(obj, tuple):
            out += obj[0].encode("latin-1") + obj[1] + obj[2].encode("latin-1")
        else:
            out += obj.encode("latin-1")
        out += b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode("latin-1")
    path.write_bytes(bytes(out))


def _strategy(**kwargs):
    return NaivePDFProcessorStrategy(extract_images=False, **kwargs)


def _bolded_pages(result):
    return tuple(
        page.page_number
        for page in result.pages
        if f"**{TITLE_CASE_LINE}**" in page.markdown
    )


def test_process_batch_is_deterministic(tmp_path):
    pdf_path = tmp_path / "determinism.pdf"
    _build_pdf(pdf_path)

    runs = []
    for _ in range(10):
        result = _strategy(batch_size=BATCH_SIZE).process_batch(pdf_path)
        runs.append(tuple(page.markdown for page in result.pages))

    assert len(set(runs)) == 1, "process_batch output varied between runs (#2319)"


def test_page_one_only_formatting_in_batch(tmp_path):
    pdf_path = tmp_path / "page_one.pdf"
    _build_pdf(pdf_path)

    for _ in range(5):
        result = _strategy(batch_size=BATCH_SIZE).process_batch(pdf_path)
        assert _bolded_pages(result) == (1,), (
            "page-1-only formatting leaked onto another page (#2319)"
        )


def test_page_numbers_sequential_in_batch(tmp_path):
    pdf_path = tmp_path / "numbering.pdf"
    _build_pdf(pdf_path, n_pages=8)

    result = _strategy(batch_size=BATCH_SIZE).process_batch(pdf_path)
    assert [page.page_number for page in result.pages] == list(range(1, 9))


@pytest.mark.parametrize("page_number", [1, 2, 3])
def test_process_page_uses_given_page_number(page_number):

    class _StubPage:
        def extract_text(self, visitor_text=None, **kwargs):
            text = "\n".join(_page_lines(page_number))
            if visitor_text is not None:
                visitor_text(text, None, [0, 0, 0, 0, 0, 0], None, None)
            return text

        def __contains__(self, key):
            return False

    strategy = _strategy()
    page = strategy._process_page(_StubPage(), None, page_number)

    assert page.page_number == page_number
    bolded = f"**{TITLE_CASE_LINE}**" in page.markdown
    assert bolded == (page_number == 1), (
        f"page-1-only formatting wrong for page_number={page_number}"
    )


def test_process_and_process_batch_agree(tmp_path):
    pdf_path = tmp_path / "parity.pdf"
    _build_pdf(pdf_path)

    serial = _strategy().process(pdf_path)
    batched = _strategy(batch_size=BATCH_SIZE).process_batch(pdf_path)

    assert [p.markdown for p in serial.pages] == [p.markdown for p in batched.pages]
    assert [p.html for p in serial.pages] == [p.html for p in batched.pages]
    assert [p.page_number for p in serial.pages] == [p.page_number for p in batched.pages]
