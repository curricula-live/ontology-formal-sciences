from pipeline.common import ROOT, checksum, read
from pipeline.rc_review import generate, stratify


def test_strata_use_a_total_budget_and_stable_rank():
    rows = [{"id": str(i), "stratum": ["major"] if i < 100 else ["rare"]} for i in range(101)]
    first = stratify(rows, 10, "test seed")
    assert first == stratify(list(reversed(rows)), 10, "test seed")
    assert len(first["sample"]) == 10
    assert first["strata"] == [
        {"stratum": ["major"], "population": 100, "selected": 10},
        {"stratum": ["rare"], "population": 1, "selected": 0},
    ]


def test_candidate_review_packet_is_reproducible_and_unassessed(tmp_path):
    directory = ROOT / "dist"
    generate(directory, tmp_path)
    generated = ROOT / "reviews/quality/rc2"
    for file in (generated / name for name in ("coverage.json", "independent-review.json")):
        assert (tmp_path / file.name).read_bytes() == file.read_bytes()
    packet = read(tmp_path / "independent-review.json")
    assert packet["manifest_sha256"] == checksum(directory / "manifest.json")
    for entry in packet["representative"].values():
        assert sum(row["selected"] for row in entry["strata"]) == len(entry["sample"])
        assert all(row["assessment"]["verdict"] == "unassessed" for row in entry["sample"])
    for group in ("critical_census", "targeted"):
        assert all(row["assessment"]["verdict"] == "unassessed"
                   for rows in packet[group].values() for row in rows)
    assert packet["critical_census"]["identity_migrations"]
