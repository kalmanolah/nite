NITE, the Nigh Impervious Task Executor
=======================================

[![Build Status](https://travis-ci.org/kalmanolah/nite.svg?branch=master)](https://travis-ci.org/kalmanolah/nite)

##About

NITE - the Nigh Impervious Task Executor - is a modular, event-driven remote
task execution framework written in Python. It aims to provide developers and
sysadmins alike with a base platform they can easily extend, allowing for fast
and stable implementations of task queues, batch processors and the like.

The name is also incredibly cool.
It should be mentioned that this project is being worked on purely for the sake
of hacking up something neat, and that it will probably not live up to your
standards.

##Configuring

Configuration will be loaded from `./config/*`, `~/.nite/config/*` and
`/etc/nite/config/*` by default. See [config](config) for the default
configuration. Please keep in mind that modules can have their own
configuration, so you should refer to module-specific documentation for details
on configuring specific modules.

##Writing modules

Everything from the entry point group `nite.modules` will be loaded by default.
To define your own module, add the following to your `setup.py`:

``` python
// setup.py
identifier = 'my_module'
entry_point = 'my_module:MyModuleClass'

setup(
    ...
    entry_points={
        'nite.modules': ['%s = %s' % (identifier, entry_point)]
    }
    ...
)
```

Module classes should extend `nite.module.AbstractModule`, which can be found
in [nite.module](nite/module.py).

##Dependencies

* python3
* amqp
* click
* setproctitle
* msgpack-python
* colorlog
* [ballercfg](https://github.com/kalmanolah/ballercfg)

##TODO

See [TODO](TODO)

##License

```
The MIT License (MIT)

Copyright (c) 2014 Kalman Olah

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
