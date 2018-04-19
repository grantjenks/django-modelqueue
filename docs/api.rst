.. automodule:: modelqueue

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
