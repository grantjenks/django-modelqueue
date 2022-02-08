ModelQueue: Task Queue Based on Django Models
=============================================

`ModelQueue`_ is an Apache2 licensed task queue based on Django models.

For example, in appname/models.py::

    import modelqueue
    from django.db import models

    class Task(models.Model):
        data = models.TextField()
        status = modelqueue.StatusField(
            # ^-- Just a models.BigIntegerField
            db_index=True,
            # ^-- Index for faster queries.
            default=modelqueue.Status.waiting,
            # ^-- Waiting state is ready to run.
        )

And in appname/management/commands/process_tasks.py::

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
                    time.sleep(1)
                    # ^-- Bring your own parallelism/concurrency.

        def process(self, task):
            pass  # Process task models.

And in appname/admin.py::

    class TaskAdmin(admin.ModelAdmin):
        actions = [*modelqueue.admin_actions('status')]
        # ^-- Change task status in admin.
        list_filter = [
            modelqueue.admin_list_filter('status'),
            # ^-- Filter tasks in admin by queue state.
        ]

        def get_changeform_initial_data(self, request):
            # v-- Automatically fill in status field when adding a new task.
            return {'status': modelqueue.Status.waiting()}

`ModelQueue`_ is a hazardous project. It takes a bad idea and makes it easy and
effective. You may come to regret using your database as a task queue but it
won't be today!

Testimonials
------------

"I didn't design relational database systems for this." ~ `Edgar Codd`_

"Well, at least you're using transactions." ~ `Jim Gray`_

"You have successfully ignored most of what's important in queueing theory." ~
`Agner Erlang`_

.. _`Edgar Codd`: https://en.wikipedia.org/wiki/Edgar_F._Codd
.. _`Jim Gray`: https://en.wikipedia.org/wiki/Jim_Gray_(computer_scientist)
.. _`Agner Erlang`: https://en.wikipedia.org/wiki/Agner_Krarup_Erlang

Does your company or website use `ModelQueue`_? Send us a `message
<contact@grantjenks.com>`_ and let us know.

Features
--------

- Pure-Python
- Supports Django's admin interface
- Tasks can be retried, aborted, and canceled
- Supports multiple attempts per task
- Bring your own parallelism with threading, multiprocessing, or asyncio
- Performance matters (add a single 64-bit field to models)
- Fully documented
- 100% test coverage
- Years of stress testing in production
- Developed on Python 3.10
- Compatible with all Django versions
- Tested on CPython 3.6, 3.7, 3.8, 3.9, 3.10
- Tested on Linux, Mac OS X, and Windows

.. image:: https://github.com/grantjenks/django-modelqueue/workflows/integration/badge.svg
   :target: https://github.com/grantjenks/django-modelqueue/actions?query=workflow%3Aintegration

.. image:: https://github.com/grantjenks/django-modelqueue/workflows/release/badge.svg
   :target: https://github.com/grantjenks/django-modelqueue/actions?query=workflow%3Arelease

Quickstart
----------

Installing `ModelQueue`_ is simple with `pip
<https://pypi.org/project/pip/>`_::

    $ python -m pip install modelqueue

You can access documentation in the interpreter with Python's built-in help
function::

    >>> import modelqueue
    >>> help(modelqueue)

User Guide
----------

For those wanting more details, this part of the documentation describes
introduction, benchmarks, development, and API.

* `ModelQueue API Reference`_

.. _`ModelQueue API Reference`: http://www.grantjenks.com/docs/modelqueue/api.html

Reference and Indices
---------------------

* `ModelQueue Documentation`_
* `ModelQueue at PyPI`_
* `ModelQueue at GitHub`_
* `ModelQueue Issue Tracker`_

.. _`ModelQueue Documentation`: http://www.grantjenks.com/docs/modelqueue/
.. _`ModelQueue at PyPI`: https://pypi.python.org/pypi/modelqueue/
.. _`ModelQueue at GitHub`: https://github.com/grantjenks/django-modelqueue/
.. _`ModelQueue Issue Tracker`: https://github.com/grantjenks/django-modelqueue/issues/

ModelQueue License
------------------

Copyright 2022 Grant Jenks

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

.. _`ModelQueue`: http://www.grantjenks.com/docs/modelqueue/
