# python-mebo

This is a library to control the [Mebo robot](http://meborobot.com/) with Python. I'm releasing it, but it's still very much a work in progress.

## Installation

`pip install mebo`

## Usage

Some basic usage is below. The API will change and no documentation exists, but it works for getting started.

```
>>> from mebo.mebo import Mebo
>>> m = Mebo(ip='192.168.1.100') # replace with IP of your mebo. You can probably get it from your router
>>> m.move('n', velocity=255, duration=1000)
>>> m.claw.open(dur=1000)
```

## Development

### Todo

- [X] Connect and control robot functions
- [ ] Discover the IP of mebo automatically?
- [ ] Cleaner API (better subclasses, kwargs for component methods, no metaprogramming)
- [ ] Documentation
- [ ] Tests
- [ ] Video capture
- [ ] Audio capture
- [ ] Audio playback

