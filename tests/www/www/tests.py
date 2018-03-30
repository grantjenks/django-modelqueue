import collections as co
import datetime as dt
import itertools
import random
import time

import modelqueue as mq
import pytest

from .models import Task


def nop(obj):
    assert mq.MIN_WORKING <= obj.status <= mq.MAX_WORKING


@pytest.mark.django_db
def test_run_waiting_finished():
    count = 10

    for num in range(count):
        task = Task(data=str(num))
        task.save()
        time.sleep(0.001)

    waiting = Task.objects.filter(
        status__gte=mq.MIN_WAITING,
        status__lte=mq.MAX_WAITING,
    )

    assert waiting.count() == count

    for num in range(count):
        tasks = Task.objects.all()
        task = mq.run(tasks, 'status', nop)
        assert task.data == str(num)

    assert mq.run(tasks, 'status', nop) is None

    finished = Task.objects.filter(
        status__gte=mq.MIN_FINISHED,
        status__lte=mq.MAX_FINISHED,
    )

    assert finished.count() == count


@pytest.mark.django_db
def test_run_created():
    count = 10

    for num in range(count):
        task = Task(data=str(num), status=mq.created())
        task.save()

    tasks = Task.objects.all()
    created = Task.objects.filter(
        status__gte=mq.MIN_CREATED,
        status__lte=mq.MAX_CREATED,
    )

    assert tasks.count() == count
    assert created.count() == count
    assert mq.run(tasks, 'status', nop) is None


@pytest.mark.django_db
def test_run_working():
    task1 = Task(data=str(0))
    task1.save()
    task2 = mq.run(Task.objects.all(), 'status', nop)
    assert task1 == task2
    state, _, _ = mq.parse(task2.status)
    assert state == mq.FINISHED


def always_fails(obj):
    assert mq.MIN_WORKING <= obj.status <= mq.MAX_WORKING
    raise RuntimeError


@pytest.mark.django_db
def test_run_canceled():
    task = Task(data=str(0))
    task.save()

    for attempt in range(3):
        try:
            mq.run(Task.objects.all(), 'status', always_fails)
        except RuntimeError:
            pass
        else:
            assert False, 'runtime error expected'

        task.refresh_from_db()
        state, _, attempts = mq.parse(task.status)
        assert state == mq.WAITING
        assert attempts == attempt + 1

    try:
        mq.run(Task.objects.all(), 'status', always_fails)
    except RuntimeError:
        pass
    else:
        assert False, 'runtime error expected'

    task.refresh_from_db()
    state, _, attempts = mq.parse(task.status)
    assert state == mq.CANCELED
    assert attempts == 4


def control_c(obj):
    assert mq.MIN_WORKING <= obj.status <= mq.MAX_WORKING
    raise KeyboardInterrupt


@pytest.mark.django_db
def test_run_canceled_no_retry():
    task = Task(data=str(0))
    task.save()

    try:
        mq.run(Task.objects.all(), 'status', control_c, retry=0)
    except KeyboardInterrupt:
        pass
    else:
        assert False, 'keyboard interrupt expected'

    task.refresh_from_db()
    state, _, attempts = mq.parse(task.status)
    assert state == mq.CANCELED
    assert attempts == 1


@pytest.mark.django_db
def test_run_timeout():
    task = Task(data=str(0))
    task.save()
    state, moment, attempts = mq.parse(task.status)
    assert state == mq.WAITING
    moment -= dt.timedelta(hours=2)
    assert attempts == 0
    task.status = mq.combine(mq.WORKING, moment, attempts)
    task.save()
    assert mq.run(Task.objects.all(), 'status', nop) == task
    task.refresh_from_db()
    state, _, attempts = mq.parse(task.status)
    assert state == mq.FINISHED
    assert attempts == 2


@pytest.mark.django_db
def test_run_future():
    future = mq.now() + mq.ONE_HOUR
    task = Task(data=str(0), status=mq.waiting(future))
    task.save()
    assert mq.run(Task.objects.all(), 'status', nop) is None


@pytest.mark.django_db
def test_run_timeout_delay():
    past = mq.now() - mq.ONE_HOUR
    task = Task(data=str(0), status=mq.working(past))
    task.save()
    assert mq.run(Task.objects.all(), 'status', nop, delay=mq.ONE_HOUR) is None
    task.refresh_from_db()
    state, _, attempts = mq.parse(task.status)
    assert state == mq.WAITING
    assert attempts == 1
    assert mq.run(Task.objects.all(), 'status', nop) is None


@pytest.mark.django_db
def test_run_error_delay():
    task = Task(data=str(0))
    task.save()
    tasks = Task.objects.all()
    try:
        mq.run(tasks, 'status', always_fails, delay=mq.ONE_HOUR)
    except RuntimeError:
        pass
    else:
        assert False, 'runtime error expected'
    task.refresh_from_db()
    state, _, attempts = mq.parse(task.status)
    assert state == mq.WAITING
    assert attempts == 1
    assert mq.run(Task.objects.all(), 'status', always_fails) is None


def maybe(obj):
    assert mq.MIN_WORKING <= obj.status <= mq.MAX_WORKING
    choice = random.randrange(3)

    if choice == 0:
        return
    elif choice == 1:
        raise RuntimeError
    else:
        assert choice == 2
        # Simulate dying in the middle of a run. ModelQueue does not handle
        # SystemExit events. The result is some tasks will be left in the
        # working state.
        raise SystemExit


def worker(counter):
    tasks = Task.objects.all()

    for num in range(10000):
        if not random.randrange(3):
            if random.randrange(100):
                task = Task(data=str(next(counter)))
            else:
                task = Task(data=str(next(counter)), status=mq.created())
            task.save()
        else:
            try:
                one_millis = dt.timedelta(microseconds=1000)
                ten_millis = one_millis * 10
                mq.run(
                    tasks,
                    'status',
                    maybe,
                    timeout=ten_millis,
                    delay=one_millis,
                )
            except BaseException:
                pass

    from django.db import connection
    connection.close()


@pytest.mark.django_db
def test_run_maybe():
    tasks = Task.objects.all()
    counter = itertools.count()
    worker(counter)

    # import threading
    # threads = []
    # for num in range(8):
    #     thread = threading.Thread(target=worker, args=(counter,))
    #     thread.start()
    #     threads.append(thread)
    # for thread in threads:
    #     thread.join()

    states = co.Counter()
    attemptses = co.Counter()

    for task in tasks:
        state, _, attempts = mq.parse(task.status)
        states[state] += 1
        attemptses[attempts] += 1

    print('')
    print('States:', sorted(states.most_common()))
    print('Attempts:', sorted(attemptses.most_common()))

    assert all(state in states for state in (1, 2, 4, 5))
    assert all(attempts in attemptses for attempts in range(5))
