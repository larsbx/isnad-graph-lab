import networkx as nx

from isnad_graph.cli import main


def test_export_and_verify_roundtrip(mini_graph, tmp_path, capsys):
    gdir = mini_graph.save(tmp_path / "g")
    assert main(["--graph", str(gdir), "verify"]) == 0
    assert main(["--graph", str(gdir), "export", str(tmp_path / "g.graphml")]) == 0
    g = nx.read_graphml(tmp_path / "g.graphml")
    assert g.number_of_edges() == mini_graph.transmissions.num_rows
    assert main(["--graph", str(gdir), "chain", "2"]) == 0
    assert "⇢" in capsys.readouterr().out


def test_tree_export(mini_graph, tmp_path):
    import json

    gdir = mini_graph.save(tmp_path / "g2")
    assert main(["--graph", str(gdir), "tree", str(tmp_path / "t.json"), "1", "2"]) == 0
    trees = json.loads((tmp_path / "t.json").read_text())
    assert [t["group_id"] for t in trees] == [1, 2]


def test_vizops_commands_report_outcomes(mini_graph, tmp_path, capsys):
    gdir = mini_graph.save(tmp_path / "g3")
    assert main(["--graph", str(gdir), "typed-graph", str(tmp_path / "t.json"), "1",
                 "--min-chains", "1"]) == 0
    assert main(["--graph", str(gdir), "page", str(tmp_path / "p.html"), "1"]) == 0
    assert main(["--graph", str(gdir), "page", str(tmp_path / "q.html"), "999"]) == 1
    assert "refused" in capsys.readouterr().out
