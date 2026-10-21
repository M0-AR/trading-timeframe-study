from tfvalidity.data.binance import window_bounds


def test_month_window_includes_last_bar():
    start, end = window_bounds("2021-01", "2021-01")
    assert str(start) == "2021-01-01 00:00:00+00:00"
    assert str(end) == "2021-01-31 23:59:59.999000+00:00"


def test_multi_month_window():
    start, end = window_bounds("2021-01", "2026-09")
    assert end.year == 2026 and end.month == 9 and end.day == 30
