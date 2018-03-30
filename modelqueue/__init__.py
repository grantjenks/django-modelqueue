"""
ModelQueue: Task Queue Based on Django Models
=============================================

Benchmarking
------------

Setup
.....

from www.models import Task
from modelqueue import run
from itertools import count
counter = count()
def noop(value):
    pass
%timeit Task(data=str(next(counter))).save()
%timeit run(Task.objects.all(), 'status', noop)

Results
.......

* SQLite; no pragmas
  * Save task: 865us
  * Run task: 3.44ms

* SQLite; journal_mode = wal; synchronous = 1
  * Save task: 238us
  * Run task: 1.86ms

* SQLite; synchronous = 0
  * Save task: 588us
  * Run task: 2.71ms

* Redis
  * Run task: 11.6us

"""

import datetime as dt
import pytz

from django.db import models
from django.db import transaction

CREATED = 1
WAITING = 2
WORKING = 3
FINISHED = 4
CANCELED = 5

MIN_CREATED = int(CREATED * 1e18)
MAX_CREATED = int((CREATED + 1) * 1e18) - 1
MIN_WAITING = int(WAITING * 1e18)
MAX_WAITING = int((WAITING + 1) * 1e18) - 1
MIN_WORKING = int(WORKING * 1e18)
MAX_WORKING = int((WORKING + 1) * 1e18) - 1
MIN_FINISHED = int(FINISHED * 1e18)
MAX_FINISHED = int((FINISHED + 1) * 1e18) - 1
MIN_CANCELED = int(CANCELED * 1e18)
MAX_CANCELED = int((CANCELED + 1) * 1e18) - 1

ONE_HOUR = dt.timedelta(hours=1)
ZERO_SECS = dt.timedelta(seconds=0)

StatusField = models.BigIntegerField


def now():
    "Return now datetime in UTC timezone."
    return dt.datetime.now(pytz.utc)


def parse(status):
    "Parse integer status into state, moment, and attempts fields."
    status = '{0:019d}'.format(status)
    assert len(status) == 19
    state = int(status[:1])
    moment = dt.datetime(
        year=int(status[1:5]),
        month=int(status[5:7]),
        day=int(status[7:9]),
        hour=int(status[9:11]),
        minute=int(status[11:13]),
        second=int(status[13:15]),
        microsecond=int(status[15:18]) * 1000,
        tzinfo=pytz.utc,
    )
    attempts = int(status[18:19])
    return state, moment, attempts


def combine(state, moment, attempts):
    "Combine state, moment, and attempts fields into integer status."
    template = (
        '{state}'
        '{year:04d}'
        '{month:02d}'
        '{day:02d}'
        '{hour:02d}'
        '{minute:02d}'
        '{second:02d}'
        '{millisecond:03d}'
        '{attempts}'
    )
    result = template.format(
        state=state,
        year=moment.year,
        month=moment.month,
        day=moment.day,
        hour=moment.hour,
        minute=moment.minute,
        second=moment.second,
        millisecond=int(moment.microsecond / 1000.0),
        attempts=attempts,
    )
    assert len(result) == 19
    return int(result)


def created(moment=None, attempts=0):
    """Return created status with given moment and attempts.

    When moment is None (the default), use now in UTC timezone.

    """
    moment = now() if moment is None else moment
    return combine(CREATED, moment, attempts)


def waiting(moment=None, attempts=0):
    """Return waiting status with given moment and attempts.

    When moment is None (the default), use now in UTC timezone.

    """
    moment = now() if moment is None else moment
    return combine(WAITING, moment, attempts)


def working(moment=None, attempts=0):
    """Return working status with given moment and attempts.

    When moment is None (the default), use now in UTC timezone.

    """
    moment = now() if moment is None else moment
    return combine(WORKING, moment, attempts)


def finished(moment=None, attempts=0):
    """Return finished status with given moment and attempts.

    When moment is None (the default), use now in UTC timezone.

    """
    moment = now() if moment is None else moment
    return combine(FINISHED, moment, attempts)


def canceled(moment=None, attempts=0):
    """Return canceled status with given moment and attempts.

    When moment is None (the default), use now in UTC timezone.

    """
    moment = now() if moment is None else moment
    return combine(CANCELED, moment, attempts)


def run(queryset, field, action, retry=3, timeout=ONE_HOUR, delay=ZERO_SECS):
    r"""Run `action` on objects from `queryset` in queue defined by `field`.

    States:

        1. CREATED
        2. WAITING
        3. WORKING
        4. FINISHED
        5. CANCELED

    Field Format:

        2  2018 03 27  14 43 25 759  0
         \    \  \  \    \  \  \  \   \
        state  \  \  \  hour \  \  \  attempt
              year \  \   minute \  \
                 month \      second \
                       day       millisecond

    """
    with transaction.atomic():
        kwargs = {field + '__gte': MIN_WORKING}
        working_query = queryset.all().filter(**kwargs)
        kwargs = {field + '__lte': working(now() - timeout)}
        working_query = working_query.filter(**kwargs)
        working_query = working_query.order_by(field)
        working_query = working_query.select_for_update()

        for worker in working_query[:1]:
            status = getattr(worker, field)
            state, _, attempts = parse(status)
            assert state == WORKING
            moment = now() + delay
            attempts += 1
            combiner = waiting if attempts <= retry else canceled
            setattr(worker, field, combiner(moment, attempts))
            worker.save()

        kwargs = {field + '__gte': MIN_WAITING}
        waiting_query = queryset.all().filter(**kwargs)
        kwargs = {field + '__lte': waiting(now())}
        waiting_query = waiting_query.filter(**kwargs)
        waiting_query = waiting_query.order_by(field)
        waiting_query = waiting_query.select_for_update()
        waiters = list(waiting_query[:1])

        if not waiters:
            return None

        worker, = waiters
        status = getattr(worker, field)
        state, _, attempts = parse(status)
        assert state == WAITING
        setattr(worker, field, working(now(), attempts))
        worker.save()

    attempts += 1

    try:
        action(worker)
    except (KeyboardInterrupt, Exception):
        with transaction.atomic():
            moment = now() + delay
            combiner = waiting if attempts <= retry else canceled
            setattr(worker, field, combiner(moment, attempts))
            worker.save()
        raise
    else:
        with transaction.atomic():
            setattr(worker, field, finished(now(), attempts))
            worker.save()

    return worker


__title__ = 'modelqueue'
__version__ = '0.0.5'
__build__ = 0x000005
__author__ = 'Grant Jenks'
__license__ = 'Apache 2.0'
__copyright__ = 'Copyright 2018 Grant Jenks'
