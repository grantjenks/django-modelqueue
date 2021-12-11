import datetime as dt
import doctest

import pytz

import modelqueue as mq


def test_title():
    assert mq.__title__ == 'modelqueue'


def test_parse_combine():
    for state1 in (1, 3, 5):
        for year in (1999, 2018, 2021):
            for month in (1, 7, 12):
                for day in (1, 8, 23, 31):
                    for hour in (0, 7, 14, 23):
                        for minute in (0, 7, 14, 59):
                            for second in (0, 7, 14, 59):
                                for microsecond in (0, 123456, 456789, 99999):
                                    for attempts1 in (0, 5, 9):
                                        priority1 = dt.datetime(
                                            year,
                                            month,
                                            day,
                                            hour,
                                            minute,
                                            second,
                                            microsecond,
                                            tzinfo=pytz.utc,
                                        )
                                        args = state1, priority1, attempts1
                                        status = mq.Status.combine(*args)
                                        result = status.parse()
                                        state2, priority2, attempts2 = result
                                        assert state1 == state2
                                        millisecond = int(microsecond / 1000.0)
                                        priority1 = priority1.replace(
                                            microsecond=millisecond * 1000,
                                        )
                                        assert priority1 == priority2
                                        assert attempts1 == attempts2


def test_states():
    priority = dt.datetime(2018, 1, 2, 3, 4, 56, 789123)
    assert mq.Status.created(priority, 1) == 1201801020304567891
    assert mq.Status.waiting(priority, 2) == 2201801020304567892
    assert mq.Status.working(priority, 3) == 3201801020304567893
    assert mq.Status.finished(priority, 4) == 4201801020304567894
    assert mq.Status.canceled(priority, 5) == 5201801020304567895


def test_doctest():
    failed, attempted = doctest.testmod(mq)
    assert failed == 0
    assert attempted > 0
