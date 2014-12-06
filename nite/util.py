"""Util module."""
import os
import errno


def get_module_attr(module_name, attr_name):
    """Return an attribute of an (un)imported module."""
    # Import the correct module
    module_ = __import__(module_name, fromlist=[attr_name])
    # Grab and return the attribute from the module
    return getattr(module_, attr_name)


def instantiate(module_name, class_name, *args, **kwargs):
    """Instantiate and return a class in an (un)imported module with arguments."""
    # Grab the class from the module
    class_ = get_module_attr(module_name, class_name)
    # Instantiate the class with our args and return the instance
    return class_(*args, **kwargs)


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
