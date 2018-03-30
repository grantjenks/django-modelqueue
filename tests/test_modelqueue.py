import datetime as dt
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
                                        moment1 = dt.datetime(
                                            year,
                                            month,
                                            day,
                                            hour,
                                            minute,
                                            second,
                                            microsecond,
                                            tzinfo=pytz.utc,
                                        )
                                        args = state1, moment1, attempts1
                                        status = mq.combine(*args)
                                        result = mq.parse(status)
                                        state2, moment2, attempts2 = result
                                        assert state1 == state2
                                        millisecond = int(microsecond / 1000.0)
                                        moment1 = moment1.replace(
                                            microsecond=millisecond * 1000,
                                        )
                                        assert moment1 == moment2
                                        assert attempts1 == attempts2


def test_states():
    moment = dt.datetime(2018, 1, 2, 3, 4, 5, 678901)
    pairs = [
        (mq.CREATED, mq.created),
        (mq.WAITING, mq.waiting),
        (mq.WORKING, mq.working),
        (mq.FINISHED, mq.finished),
        (mq.CANCELED, mq.canceled),
    ]
    for state, func in pairs:
        assert func(moment, 9) == mq.combine(state, moment, 9)
