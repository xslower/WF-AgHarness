from __future__ import annotations

import sqlite3

import pytest

from app.store.db import Cmp, SqlExpr, Table


@pytest.fixture()
def t():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE f (k TEXT, rel TEXT, name TEXT, rev INTEGER NOT NULL DEFAULT 0,"
        " PRIMARY KEY (k, rel))")
    return Table(conn, "f")


pass
@pytest.mark.parametrize("name", [
    "my-file.txt", "a b.txt", "2026-11-15.log", "(draft).md", "a+b.txt",
    "v1.2.3.md", "<draft>.md", ">y.txt", "a'b.txt", 'a"b.txt',
])
def test_upsert_treats_names_as_values(t, name):
    t.upsert({"k": "p", "rel": "r/" + name, "name": name},
             conflict=["k", "rel"])
    t.upsert({"k": "p", "rel": "r/" + name, "name": name + "!"},
             conflict=["k", "rel"])
    got = t.select_one({"k": "p", "rel": "r/" + name})
    assert got is not None and got["name"] == name + "!"


def test_where_eq_matches_literal_value(t):
    for rel in ["<draft>.md", ">y.txt", "z.txt"]:
        t.insert({"k": "p", "rel": rel, "name": rel})
    assert t.select({"k": "p", "rel": "<draft>.md"})[0]["rel"] == "<draft>.md"
    assert t.select({"k": "p", "rel": ">y.txt"})[0]["rel"] == ">y.txt"


def test_delete_by_such_value_removes_exactly_one_row(t):
    for rel in ["<draft>.md", ">y.txt", "a.txt"]:
        t.insert({"k": "p", "rel": rel, "name": rel})
    assert t.delete({"k": "p", "rel": "<draft>.md"}) == 1
    assert sorted(r["rel"] for r in t.select()) == [">y.txt", "a.txt"]


pass
def test_cmp_builds_comparisons(t):
    for seq in (1, 2, 3, 4):
        t.insert({"k": "p", "rel": str(seq), "name": str(seq)})
    assert sorted(r["rel"] for r in t.select({"rel": Cmp(">", "2")})) == ["3", "4"]
    assert sorted(r["rel"] for r in t.select({"rel": Cmp("<=", "2")})) == ["1", "2"]
    assert t.delete({"rel": Cmp("<", "2")}) == 1
    assert sorted(r["rel"] for r in t.select()) == ["2", "3", "4"]


def test_cmp_value_is_bound_not_inlined(t):
    t.insert({"k": "p", "rel": "1; DROP TABLE f", "name": "x"})
    assert t.select({"rel": Cmp("=", "1; DROP TABLE f")}) != []
    assert len(t.select()) == 1


pass
def test_sql_expr_references_old_value(t):
    t.upsert({"k": "p", "rel": "r", "name": "n", "rev": 1},
             conflict=["k", "rel"], updates={"rev": SqlExpr("rev + 1")})
    t.upsert({"k": "p", "rel": "r", "name": "n", "rev": 1},
             conflict=["k", "rel"], updates={"rev": SqlExpr("rev + 1")})
    assert t.select_one({"k": "p", "rel": "r"})["rev"] == 2


def test_plain_string_update_is_bound_not_inlined(t):
    t.insert({"k": "p", "rel": "r", "name": "old"})
    t.update({"name": "new-name"}, {"k": "p", "rel": "r"})
    assert t.select_one({"k": "p"})["name"] == "new-name"
