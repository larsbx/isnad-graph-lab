import hashlib

from vizops.figure import CAVEAT
from vizops.outcome import Refused, Rendered

from isnad_graph.atlas import build


def test_page_is_stamped_and_reported_as_rendered(mini_graph, tmp_path):
    out = build(mini_graph, tmp_path / "atlas.html", groups=(1, 2))
    assert isinstance(out, Rendered)
    html = (tmp_path / "atlas.html").read_text()
    assert out.digest == hashlib.sha256(html.encode()).hexdigest()
    assert "larsbx/isnad-graph-lab/data/graph @ sha256:" in html and CAVEAT in html
    assert "__DATA__" not in html and "__STAMP__" not in html and "__SCOPE__" not in html
    assert "every recorded chain of 2 reports," in html  # the scope is the data's, not fixed


def test_scope_follows_the_groups_asked_for(mini_graph, tmp_path):
    build(mini_graph, tmp_path / "one.html", groups=(1,))
    assert "every recorded chain of 1 report," in (tmp_path / "one.html").read_text()


def test_a_group_without_chains_is_refused(mini_graph, tmp_path):
    out = build(mini_graph, tmp_path / "atlas.html", groups=(1, 999))
    assert isinstance(out, Refused) and "999" in out.reason
    assert not (tmp_path / "atlas.html").exists()
