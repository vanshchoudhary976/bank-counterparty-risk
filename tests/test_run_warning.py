from credit_risk.warning.run_warning import WINDOWS


def test_windows_cover_the_blueprint_periods():
    start, end = WINDOWS["2008 to 2012 failures"]
    assert start.year == 2008 and end.year == 2012
    assert WINDOWS["2023 cases"][1].year == 2023
