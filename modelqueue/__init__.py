"""ModelQueue API Reference
===========================

:doc:`ModelQueue <index>` is an Apache2 licensed task queue based on Django models.

The examples below assume the following in appname/models.py::

    import modelqueue
    from django.db import models

    class Task(models.Model):
        data = models.TextField()
        status = modelqueue.StatusField(
            db_index=True,
            # ^-- Index for faster queries.
            default=modelqueue.Status.waiting,
            # ^-- Waiting state is ready to run.
        )

"""

import datetime as dt
import pytz

from django.contrib import admin
from django.db import models
from django.db import transaction

ONE_HOUR = dt.timedelta(hours=1)
ZERO_SECS = dt.timedelta(seconds=0)

StatusField = models.BigIntegerField


def now():
    "Return now datetime in UTC timezone."
    return dt.datetime.now(pytz.utc)


class State(int):
    """Model Queue State

    >>> state = State(1, 'created')
    >>> assert state == 1
    >>> assert state.name == 'created'
    >>> print(state)
    created
    >>> repr(state)
    "State(1, 'created')"
    >>> State.created
    State(1, 'created')

    """
    def __new__(cls, value, name):
        state = super(State, cls).__new__(cls, value)
        state.name = name
        return state


    def __str__(self):
        return self.name


    def __repr__(self):
        type_name = type(self).__name__
        return '{}({!r}, {!r})'.format(type_name, int(self), self.name)


class Status(int):
    """Model Queue Status

    64-bit Signed Integer Field Format::

        state        priority          attempt
          |   |----------------------|   |
          2   2018 03 27  14 43 25 759   0
               |   |   |   |  |  |  |
               |   |   | hour |  |  |
              year |   |  minute |  |
                 month |     second |
                      day       millisecond

    >>> status = Status(3201801020304567896)
    >>> assert status.state == State.working
    >>> assert status.priority == 20180102030456789
    >>> assert status.attempts == 6
    >>> Status.canceled(123, 5)
    Status(5000000000000001235)

    """
    _state_offset = 1000000000000000000
    states = [
        State(1, 'created'),
        State(2, 'waiting'),
        State(3, 'working'),
        State(4, 'finished'),
        State(5, 'canceled'),
    ]
    max_attempts = 9


    @property
    def state(self):
        """Return state of status.

        >>> status = Status(3201801020304567896)
        >>> status.state
        State(3, 'working')

        """
        num = self // self._state_offset
        return next(state for state in self.states if state == num)


    @property
    def priority(self):
        """Return priority of status.

        >>> status = Status(3201801020304567896)
        >>> status.priority
        20180102030456789

        """
        return int(format(self, '019d')[1:-1])


    @property
    def attempts(self):
        """Return attempts of status.

        >>> status = Status(3201801020304567896)
        >>> status.attempts
        6

        """
        return self % 10


    @classmethod
    def filter(cls, field, state):
        """Return keyword arguments to filter `field` by `state` for querysets.

        For example::

            Task.objects.filter(**Status.filter('fieldname', State.working))

        :param str field: field name
        :param State state: model queue state
        :returns: keyword arguments

        >>> kwargs = Status.filter('status', State.waiting)
        >>> assert len(kwargs) == 2
        >>> assert kwargs['status__gte'] == Status.minimum(State.waiting)
        >>> assert kwargs['status__lte'] == Status.maximum(State.waiting)
        >>> value = Status.filter('status', 'waiting')
        >>> assert kwargs == value

        """
        if isinstance(state, str):
            state = getattr(State, state)
        assert isinstance(state, State)
        kwargs = {
            field + '__gte': Status.minimum(state),
            field + '__lte': Status.maximum(state),
        }
        return kwargs


    @classmethod
    def minimum(cls, state):
        """Calculate status minimum value given `state`.

        >>> Status.minimum(State.working)
        3000000000000000000
        >>> Status.minimum('working')
        3000000000000000000

        :param state: status state
        :returns: minimum status value with given state

        """
        if isinstance(state, str):
            state = getattr(State, state)
        return state * cls._state_offset


    @classmethod
    def maximum(cls, state):
        """Calculate status maximum value given `state`.

        >>> Status.maximum(State.working)
        3999999999999999999
        >>> Status.maximum('working')
        3999999999999999999

        :param state: status state
        :returns: maximum status value with given state

        """
        if isinstance(state, str):
            state = getattr(State, state)
        return (state + 1) * cls._state_offset - 1


    @classmethod
    def tally(cls, queryset, field):
        """Return mapping of state to count from `field` in `queryset`.

        For example::

            Status.tally(Task.objects.all(), 'status')

        :param queryset: Django queryset
        :param str field: field name
        :returns: mapping of state names to counts

        """
        result = {}
        for state in Status.states:
            kwargs = cls.filter(field, state)
            result[state.name] = queryset.all().filter(**kwargs).count()
        return result


    @classmethod
    def combine(cls, state, priority, attempts):
        """Combine `state`, `priority`, and `attempts` fields into status.

        >>> Status.combine(State.waiting, 0, 1)
        Status(2000000000000000001)
        >>> Status.combine('waiting', 0, 2)
        Status(2000000000000000002)
        >>> priority = dt.datetime(2018, 1, 2, 3, 4, 56, 789123)
        >>> Status.combine(State.waiting, priority, 3)
        Status(2201801020304567893)

        """
        if isinstance(state, str):
            state = getattr(State, state)

        if isinstance(priority, dt.datetime):
            template = (
                '{year:04d}'
                '{month:02d}'
                '{day:02d}'
                '{hour:02d}'
                '{minute:02d}'
                '{second:02d}'
                '{millisecond:03d}'
            )
            priority = int(template.format(
                year=priority.year,
                month=priority.month,
                day=priority.day,
                hour=priority.hour,
                minute=priority.minute,
                second=priority.second,
                millisecond=int(priority.microsecond / 1000.0),
            ))

        result = '{state}{priority:017d}{attempts}'.format(
            state=int(state),
            priority=priority,
            attempts=attempts,
        )
        assert len(result) == 19
        return Status(result)


    def parse(self, datetime=True):
        """Parse status into state, priority, and attempts fields.

        If `datetime` is True (the default), then parse priority into datetime
        object. Priority has format::

                   priority
            |----------------------|
            2018 03 27  14 43 25 759
             |   |   |   |  |  |  |
             |   |   | hour |  |  |
            year |   |  minute |  |
               month |     second |
                    day       millisecond

        :param bool datetime: parse priority as datetime (default True)
        :returns: tuple of state, priority, and attempts

        >>> status = Status(1201801020304567895)
        >>> state, priority, attempts = status.parse()
        >>> state
        State(1, 'created')
        >>> priority
        datetime.datetime(2018, 1, 2, 3, 4, 56, 789000, tzinfo=<UTC>)
        >>> attempts
        5
        >>> status = Status(3000000000000000007)
        >>> status.parse(datetime=False)
        (State(3, 'working'), 0, 7)

        """
        priority = self.priority
        if datetime:
            priority = str(priority)
            priority = dt.datetime(
                year=int(priority[0:4]),
                month=int(priority[4:6]),
                day=int(priority[6:8]),
                hour=int(priority[8:10]),
                minute=int(priority[10:12]),
                second=int(priority[12:14]),
                microsecond=int(priority[14:17]) * 1000,
                tzinfo=pytz.utc,
            )
        return self.state, priority, self.attempts


    def __repr__(self):
        type_name = type(self).__name__
        return '{}({})'.format(type_name, int(self))


def _make_status_method(state):
    def status(cls, priority=None, attempts=0):
        """Return new {name} status with given priority and attempts.

        When `priority` is None (the default), uses `now()`.

        :param priority: integer or datetime, lower is higher priority
        :param int attempts: number of previous attempts (0 through 9)
        :returns: status

        """
        priority = now() if priority is None else priority
        return cls.combine(state, priority, attempts)
    status.__name__ = state.name
    status.__doc__ = status.__doc__.format(name=state.name)
    return status


for _state in Status.states:
    setattr(State, _state.name, _state)
    setattr(Status, _state.name, classmethod(_make_status_method(_state)))


def run(queryset, field, action, retry=3, timeout=ONE_HOUR, delay=ZERO_SECS):
    """Run `action` on results from `queryset` in queue defined by `field`.

    For example in appname/management/commands/process_tasks.py::

        import modelqueue, time
        from django.core.management.base import BaseCommand
        from .models import Task

        class Command(BaseCommand):

            def handle(self, *args, **options):
                while True:
                    task = modelqueue.run(
                        Task.objects.all(),
                        # ^-- Queryset of models to process.
                        'status',
                        # ^-- Field name for model queue.
                        self.process,
                        # ^-- Callable to process model.
                    )
                    if task is None:
                        time.sleep(0.1)
                        # ^-- Bring your own parallelism/concurrency.

            def process(self, report):
                pass  # Process task models.

    :param queryset: Django queryset
    :param str field: field name
    :param function action: applied to models from `queryset`
    :param int retry: max retry count (limit 8)
    :param timedelta timeout: max runtime for `action`
    :param timedelta delay: delay time after retry
    :return: model from queryset or None if no waiting model

    """
    assert 0 <= retry <= 8
    with transaction.atomic():
        kwargs = {field + '__gte': Status.minimum(State.working)}
        working_query = queryset.all().filter(**kwargs)
        max_working = Status.working(now() - timeout, Status.max_attempts)
        kwargs = {field + '__lte': max_working}
        working_query = working_query.filter(**kwargs)
        working_query = working_query.order_by(field)
        working_query = working_query.select_for_update()

        for worker in working_query[:1]:
            status = Status(getattr(worker, field))
            assert status.state == State.working
            priority = now() + delay
            attempts = status.attempts + 1
            state = Status.waiting if attempts <= retry else Status.canceled
            setattr(worker, field, state(priority, attempts))
            worker.save()

        kwargs = {field + '__gte': Status.minimum(State.waiting)}
        waiting_query = queryset.all().filter(**kwargs)
        max_waiting = Status.waiting(now(), Status.max_attempts)
        kwargs = {field + '__lte': max_waiting}
        waiting_query = waiting_query.filter(**kwargs)
        waiting_query = waiting_query.order_by(field)
        waiting_query = waiting_query.select_for_update()
        waiters = list(waiting_query[:1])

        if not waiters:
            return None

        worker, = waiters
        status = Status(getattr(worker, field))
        assert status.state == State.waiting
        attempts = status.attempts
        setattr(worker, field, Status.working(now(), attempts))
        worker.save()

    attempts += 1

    try:
        action(worker)
    except (KeyboardInterrupt, Exception):
        with transaction.atomic():
            priority = now() + delay
            state = Status.waiting if attempts <= retry else Status.canceled
            setattr(worker, field, state(priority, attempts))
            worker.save()
        raise
    else:
        with transaction.atomic():
            setattr(worker, field, Status.finished(now(), attempts))
            worker.save()

    return worker


def admin_list_filter(field):
    """Return Django admin list filter for `field` describing model queue.

    For example in appname/admin.py::

        class TaskAdmin(admin.TaskAdmin):
            list_filter = [
                modelqueue.admin_list_filter('status'),
                # ^-- Filter tasks in admin by queue state.
            ]

    :param str field: field name
    :returns: Django admin model queue list filter

    """
    class QueueFilter(admin.SimpleListFilter):
        "Django admin ModelQueue list filter."
        title = '%s queue status' % field
        parameter_name = '%s_queue' % field


        def lookups(self, request, model_admin):
            return (
                (State.created, 'Created'),
                (State.waiting, 'Waiting'),
                (State.working, 'Working'),
                (State.finished, 'Finished'),
                (State.canceled, 'Canceled'),
            )


        def queryset(self, request, queryset):
            value = self.value()

            if value is None:
                return queryset

            state = getattr(State, value)
            kwargs = Status.filter(field, state)
            return queryset.filter(**kwargs)

    return QueueFilter


__title__ = 'modelqueue'
__version__ = '1.0.0'
__build__ = 0x010000
__author__ = 'Grant Jenks'
__license__ = 'Apache 2.0'
__copyright__ = 'Copyright 2018 Grant Jenks'
