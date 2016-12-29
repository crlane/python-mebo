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
    # replace with IP of your mebo. You can probably get it from your router. Autodiscovery is coming
    m = Mebo(ip='192.168.1.100') 
    # supported directions ('n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw',)
    # velocity is how fast the wheels turn (yes, it's technically speed, but originally I had a sign on velocity.
    # Then I discovered that there were cardinal direction api calls and had to change it
    m.move('n', velocity=255, duration=1000) 
    # dur is the value taken by the API. I'll clean it up soon - values < 1000 ms don't work
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

* [X] Connect and control robot functions
* [ ] Discover the IP of mebo automatically?
* [ ] Cleaner API (better subclasses, kwargs for component methods, no metaprogramming)
* [ ] Clean up kwargs inconsistency
* [ ] Documentation
* [ ] Tests
* [ ] Video capture
* [ ] Audio capture
* [ ] Audio playback

