Django Model Queue API Reference
================================

.. contents::
   :local:

The examples below assume the following models::

    import modelqueue
    from django.db import models

    class Task(models.Model):
        data = models.TextField()
        status = modelqueue.StatusField(
            db_index=True,
            default=modelqueue.Status.waiting,
        )

Functions
---------

.. autofunction:: modelqueue.run

.. autofunction:: modelqueue.admin_list_filter

.. autofunction:: modelqueue.now

State
-----

.. autoclass:: modelqueue.State

   .. autoattribute:: created
   .. autoattribute:: waiting
   .. autoattribute:: working
   .. autoattribute:: finished
   .. autoattribute:: canceled

Status
------

.. autoclass:: modelqueue.Status
   :members:

   .. autoattribute:: states

StatusField
-----------

.. autoclass:: modelqueue.StatusField

Constants
---------

.. data:: modelqueue.ONE_HOUR

.. data:: modelqueue.ZERO_SECS
