import collections as co
import datetime as dt
import itertools
import random
import time

import modelqueue as mq
import pytest

from django.contrib.auth.models import User
from django.test import Client

from .models import Task


def nop(obj):
    min_working = mq.Status.minimum(mq.State.working)
    max_working = mq.Status.maximum(mq.State.working)
    assert min_working <= obj.status <= max_working



@pytest.mark.django_db
def test_run_waiting_finished():
    count = 10

    for num in range(count):
        task = Task(data=str(num))
        task.save()
        time.sleep(0.001)

    waiting_kwargs = mq.Status.filter('status', mq.State.waiting)
    waiting = Task.objects.filter(**waiting_kwargs)
    assert waiting.count() == count

    for num in range(count):
        tasks = Task.objects.all()
        task = mq.run(tasks, 'status', nop)
        assert task.data == str(num)

    assert mq.run(tasks, 'status', nop) is None

    finished_kwargs = mq.Status.filter('status', mq.State.finished)
    finished = Task.objects.filter(**finished_kwargs)
    assert finished.count() == count


@pytest.mark.django_db
def test_run_created():
    count = 10

    for num in range(count):
        task = Task(data=str(num), status=mq.Status.created())
        task.save()

    tasks = Task.objects.all()
    assert tasks.count() == count

    created_kwargs = mq.Status.filter('status', mq.State.created)
    created = Task.objects.filter(**created_kwargs)
    assert created.count() == count

    assert mq.run(tasks, 'status', nop) is None


@pytest.mark.django_db
def test_run_working():
    task1 = Task(data=str(0))
    task1.save()
    task2 = mq.run(Task.objects.all(), 'status', nop)
    assert task1 == task2
    assert mq.Status(task2.status).state == mq.State.finished


def always_fails(obj):
    nop(obj)
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
        status = mq.Status(task.status)
        assert status.state == mq.State.waiting
        assert status.attempts == attempt + 1

    try:
        mq.run(Task.objects.all(), 'status', always_fails)
    except RuntimeError:
        pass
    else:
        assert False, 'runtime error expected'

    task.refresh_from_db()
    status = mq.Status(task.status)
    assert status.state == mq.State.canceled
    assert status.attempts == 4


def control_c(obj):
    nop(obj)
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
    status = mq.Status(task.status)
    assert status.state == mq.State.canceled
    assert status.attempts == 1


@pytest.mark.django_db
def test_run_timeout():
    task = Task(data=str(0))
    task.save()
    state, priority, attempts = mq.Status(task.status).parse()
    assert state == mq.State.waiting
    priority -= dt.timedelta(hours=2)
    assert attempts == 0
    task.status = mq.Status.working(priority, 0)
    task.save()
    assert mq.run(Task.objects.all(), 'status', nop) == task
    task.refresh_from_db()
    status = mq.Status(task.status)
    assert status.state == mq.State.finished
    assert status.attempts == 2


@pytest.mark.django_db
def test_run_future():
    future = mq.now() + mq.ONE_HOUR
    task = Task(data=str(0), status=mq.Status.waiting(future))
    task.save()
    assert mq.run(Task.objects.all(), 'status', nop) is None


@pytest.mark.django_db
def test_run_timeout_delay():
    past = mq.now() - mq.ONE_HOUR
    task = Task(data=str(0), status=mq.Status.working(past))
    task.save()
    assert mq.run(Task.objects.all(), 'status', nop, delay=mq.ONE_HOUR) is None
    task.refresh_from_db()
    status = mq.Status(task.status)
    assert status.state == mq.State.waiting
    assert status.attempts == 1
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
    status = mq.Status(task.status)
    assert status.state == mq.State.waiting
    assert status.attempts == 1
    assert mq.run(Task.objects.all(), 'status', always_fails) is None


def maybe(obj):
    nop(obj)
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
                status = mq.Status.created()
                task = Task(data=str(next(counter)), status=status)
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
        status = mq.Status(task.status)
        states[status.state] += 1
        attemptses[status.attempts] += 1

    print()
    print('States:', sorted(states.most_common()))
    print('Attempts:', sorted(attemptses.most_common()))

    assert all(state in states for state in (1, 2, 4, 5))
    assert all(attempts in attemptses for attempts in range(5))


def raise_retry(obj):
    nop(obj)
    raise mq.Retry(dt.timedelta(seconds=7))


@pytest.mark.django_db
def test_raise_retry():
    task = Task(data=str(0))
    task.save()
    before_status = mq.Status(task.status)
    task = mq.run(Task.objects.all(), 'status', raise_retry)
    task.refresh_from_db()
    after_status = mq.Status(task.status)
    assert after_status.state == mq.State.waiting
    assert after_status.priority >= before_status.priority
    assert after_status.attempts == 0


def raise_abort(obj):
    nop(obj)
    raise mq.Abort(dt.timedelta(seconds=7))


@pytest.mark.django_db
def test_raise_abort():
    task = Task(data=str(0))
    task.save()
    before_status = mq.Status(task.status)
    task = mq.run(Task.objects.all(), 'status', raise_abort)
    task.refresh_from_db()
    after_status = mq.Status(task.status)
    assert after_status.state == mq.State.waiting
    assert after_status.priority >= before_status.priority
    assert after_status.attempts == 1


def raise_cancel(obj):
    nop(obj)
    raise mq.Cancel


@pytest.mark.django_db
def test_raise_cancel():
    task = Task(data=str(0))
    task.save()
    before_status = mq.Status(task.status)
    task = mq.run(Task.objects.all(), 'status', raise_cancel)
    task.refresh_from_db()
    after_status = mq.Status(task.status)
    assert after_status.state == mq.State.canceled
    assert after_status.priority >= before_status.priority
    assert after_status.attempts == 1


@pytest.mark.django_db
def test_tally():
    result = {
        'created': 1,
        'waiting': 2,
        'working': 3,
        'finished': 4,
        'canceled': 5,
    }

    for state in mq.Status.states:
        for num in range(state):
            func = getattr(mq.Status, str(state))
            task = Task(data=str(int(state)), status=func())
            task.save()

    tasks = Task.objects.all()
    assert mq.Status.tally(tasks, 'status') == result


@pytest.mark.django_db
def test_admin_list_filter():
    user = User.objects.create(username='alice', password='password')
    user.is_superuser = True
    user.is_staff = True
    user.save()

    client = Client()
    client.force_login(user)

    for state in mq.Status.states:
        for num in range(state * 2):
            func = getattr(mq.Status, str(state))
            task = Task(data=str(int(state)), status=func())
            task.save()

    response = client.get('/admin/www/task/')
    assert b'30 tasks' in response.content

    for state in mq.Status.states:
        url = '/admin/www/task/?status_queue={name}'.format(name=state.name)
        response = client.get(url)
        assert '{} tasks'.format(state * 2).encode() in response.content
