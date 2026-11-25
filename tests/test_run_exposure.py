from credit_risk.exposure.run_exposure import read_counterparties


def test_read_counterparties_rejects_missing_label(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("label,cert,name,grade,selection_quarter\nREAL,1,Bank,3,2022-12-31\n")
    try:
        read_counterparties(p)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_read_counterparties_parses_rows(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("label,cert,name,grade,selection_quarter\nILLUSTRATIVE,7,Bank A,4,2022-12-31\n")
    (cp,) = read_counterparties(p)
    assert (cp.cert, cp.name, cp.grade) == (7, "Bank A", 4)
