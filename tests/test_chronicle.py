import json
import re

from vizops.outcome import Refused, Rendered

from isnad_graph.chronicle import build, payload


def test_payload_is_per_century_and_conserves_chains(mini_graph):
    p = payload(mini_graph, min_chains=1)
    assert p["centuries"] and set(map(int, p["homes"])) <= set(p["centuries"])
    for c, flows in p["flows"].items():
        assert all(s != d for s, d, _ in flows)
        assert sum(n for *_, n in flows) <= sum(p["homes"][c].values())
    assert sum(p["ages"]["counts"]) == p["ages"]["n"]
    assert {r["uri"] for r in p["places"]} >= {u for h in p["homes"].values() for u in h}


def test_page_is_stamped(mini_graph, tmp_path):
    out = build(mini_graph, tmp_path / "c.html", min_chains=1)
    assert isinstance(out, Rendered)
    html = (tmp_path / "c.html").read_text()
    assert "__DATA__" not in html and "sha256:" in html
    data = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S)[1].replace("<\\/", "</"))
    assert data["centuries"] == payload(mini_graph, min_chains=1)["centuries"]


def test_the_page_draws_without_a_basemap(mini_graph, tmp_path):
    assert payload(mini_graph, min_chains=1, basemap_dir=tmp_path / "none")["basemap"] == {}
    assert isinstance(build(mini_graph, tmp_path / "c.html", 1, tmp_path / "none"), Rendered)


def test_nothing_to_draw_is_refused(mini_graph, tmp_path):
    assert isinstance(build(mini_graph, tmp_path / "x.html", min_chains=10**9), Refused)
    assert not (tmp_path / "x.html").exists()
