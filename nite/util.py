"""Util module."""
import os
import errno
import signal


def get_module_attr(module_name, attr_name):
    """Return an attribute of an (un)imported module."""
    # Import the correct module
    module_ = __import__(module_name, fromlist=[attr_name])
    # Grab and return the attribute from the module
    return getattr(module_, attr_name)


def instantiate(module_name, class_name, *args):
    """Instantiate and return a class in an (un)imported module with arguments."""
    # Grab the class from the module
    class_ = get_module_attr(module_name, class_name)
    # Instantiate the class with our args and return the instance
    return class_(*args)


def ensure_dir(dir_name):
    """Ensure that a directory exists.

    Taken from: http://stackoverflow.com/a/21349806

    """
    try:
        os.makedirs(dir_name)
    except OSError as err:
        if err.errno != errno.EEXIST:
            raise
    return


def set_working_directory():
    """Set the current working directory to the root of the application."""
    os.chdir(os.path.realpath(__file__).replace('nite/util.py', ''))


def enum(*sequential, **named):
    """Enum support for python < 3.4. Construct and return an enum.

    Taken from http://stackoverflow.com/a/1695250.

    """
    enums = dict(zip(sequential, range(len(sequential))), **named)

    reverse = dict((value, key) for key, value in enums.items())
    enums['reverse_mapping'] = reverse

    return type('Enum', (), enums)


def ignore_signals():
    """Help worker processes ignore useless signals.

    This helps prevent worker processes getting killed by anyone but the master process.

    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
