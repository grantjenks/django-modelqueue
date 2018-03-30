ModelQueue: Task Queue Based on Django Models
=============================================

`ModelQueue`_ is an Apache2 licenced task queue based on Django models.

.. warning::

   What you see here is a work-in-progress!

Here's what it looks like:

::

    # yourapp/models.py

    import modelqueue
    from django.db import models

    class Report(models.Model):
        upload = models.FileField()
        status = modelqueue.StatusField(
        # ^-- Add status field.
            db_index=True,
            # ^-- Add index for faster queries.
            default=modelqueue.waiting,
            # ^-- Set default state to WAITING.
        )

    # yourapp/management/commands/process_report_uploads.py

    import modelqueue, time
    from django.core.management.base import BaseCommand

    class Command(BaseCommand):

        def handle(self, *args, **options):
            while True:
                modelqueue.run(
                    Report.objects.all(),
                    # ^-- Queryset of models to process.
                    'status',
                    # ^-- Field name for model queue.
                    self.process,
                    # ^-- Callable to process model.
                )
                time.sleep(0.001)
                # ^-- Bring your own parallelism/concurrency.

        def process(self, report):
            pass  # Process report uploads.

ModelQueue is a hazardous project. It takes a bad idea and makes it easy and
effective. You may come to regret using your database as a task queue but it
won't be today!

Testimonials
------------

"I didn't design relational database systems for this." ~ `Edgar F. Codd`_

"Well at least you're using transactions." ~ `Jim Gray`_

"You have successfully ignored most of what's important in queueing theory." ~
`Agner Krarup Erlang`_

.. _`Edgar F. Codd`: https://en.wikipedia.org/wiki/Edgar_F._Codd
.. _`Jim Gray`: https://en.wikipedia.org/wiki/Jim_Gray_(computer_scientist)
.. _`Agner Krarup Erlang`: https://en.wikipedia.org/wiki/Agner_Krarup_Erlang

Does your company or website use `ModelQueue`_? Send us a `message
<contact@grantjenks.com>`_ and let us know.

Features
--------

- Pure-Python
- Performance matters
- 100% test coverage
- Hours of stress testing
- Developed on Python 3.6
- Tested on Django 1.11
- Tested on CPython 2.7, 3.4, 3.5, 3.6, PyPy and PyPy3
- Tested on Linux, Mac OS X, and Windows
- Tested using Travis CI and AppVeyor CI

.. image:: https://api.travis-ci.org/grantjenks/django-modelqueue.svg?branch=master
    :target: http://www.grantjenks.com/docs/modelqueue/

.. image:: https://ci.appveyor.com/api/projects/status/github/grantjenks/django-modelqueue?branch=master&svg=true
    :target: http://www.grantjenks.com/docs/modelqueue/

.. todo::

   - Fully documented
   - Benchmark comparisons
   - Tested on Django 2.0

Quickstart
----------

Installing ModelQueue is simple with `pip
<https://pypi.python.org/pypi/pip>`_::

  $ pip install modelqueue

You can access documentation in the interpreter with Python's built-in help
function::

  >>> import modelqueue
  >>> help(modelqueue)
  >>> help(modelqueue.StatusField)
  >>> help(modelqueue.run)

User Guide
----------

For those wanting more details, this part of the documentation describes
introduction, benchmarks, development, and API.

.. todo::

   * `ModelQueue Tutorial`_
   * `ModelQueue Benchmarks`_
   * `ModelQueue API Reference`_
   * `ModelQueue Development`_

.. _`ModelQueue Tutorial`: http://www.grantjenks.com/docs/modelqueue/tutorial.html
.. _`ModelQueue Benchmarks`: http://www.grantjenks.com/docs/modelqueue/benchmarks.html
.. _`ModelQueue API Reference`: http://www.grantjenks.com/docs/modelqueue/api.html
.. _`ModelQueue Development`: http://www.grantjenks.com/docs/modelqueue/development.html

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

Copyright 2018 Grant Jenks

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
