mebo
----

Mebo is a python package to control the `Mebo Robot <https://meborobot.com>` with Python. 

This is a beta, so there might be breaking changes. Some basic usage is defined below, but more extensive `documentation is available at ReadTheDocs <https://python-mebo.readthedocs.io/en/latest/>`_.

.. note::
    This project is not associated with the official Mebo project or its owners, Skyrocket LLC.

.. note::

    This package and the associated modules have been tested on Mebo version 1 *only*.


Installation
---------------

.. code:: 

   pip install mebo


Quickstart
----------

Some basic usage is below. The API will change and limited documentation exists, but it works for getting started.

.. code:: python

    from mebo import Mebo
    m = Mebo() # autodiscover IP using mDNS
    m.move('n', speed=255, dur=1000)  # move forward at max speed for 1 second
    m.arm.up(dur=1000) # move the arm up for one second
    m.claw.open(dur=1000) # open the claw for one second


Architecture
------------
The Mebo is controlled via an HTTP API. You can read more about it in the Mebo API repo. 


Development
-----------

Requirements:
~~~~~~~~~~~~~
* python >= 3.6

To get started with the project:

.. code:: 

    git clone https://github.com/crlane/python-mebo.git
    python -m venv mebo-venv
    . mebo-venv/bin/actvate
    pip install -e '.[dev]'

To run the tests:

.. code::

    py.test
