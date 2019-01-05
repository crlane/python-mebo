===========
python-mebo
===========

This is a library to control the [Mebo robot](http://meborobot.com/) with Python. I'm releasing it, but it's still very much a work in progress.

Installation
---------------

``pip install mebo``



Usage
--------

Some basic usage is below. The API will change and no documentation exists, but it works for getting started.

.. code:: python
    from mebo.mebo import Mebo
    # autodiscover the mebo robot on your local network using mDNS
    m = Mebo() 
    # supported directions ('n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw',)
    # dur is the value taken by the API
    m.move('n', speed=255, dur=1000) 
    m.claw.open(dur=1000) 


Development
-----------

Requirements:
~~~~~~~~~~~~~
* Docker
* make

See Makefile for instructions commands. To build image and run tests:

``make``

Todo
~~~~

* [ ] Cleaner API (better subclasses, kwargs for component methods, no metaprogramming)
* [ ] Clean up kwargs inconsistency
* [ ] Documentation
* [ ] Tests
* [ ] Media stream (multithreading or asyncio, http with <video> tag)

