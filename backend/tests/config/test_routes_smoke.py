
import pytest

ENDPOINTS = [
    "/api/config",
    "/api/sessions",
    "/api/projects/tree",
    "/api/workflows",
    "/api/approvals",
]


@pytest.mark.parametrize("path", ENDPOINTS)
def test_router_smoke(client, path):
    r = client.get(path)
    assert r.status_code == 200, r.text


def test_main_entry_is_thin():
    from pathlib import Path
    import app
    p = Path(app.__file__).resolve().parent / "main.py"
    assert len(p.read_text("utf-8").splitlines()) <= 150
