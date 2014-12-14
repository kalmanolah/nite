"""Module module."""
import sys
import logging
from pkg_resources import iter_entry_points


logger = logging.getLogger(__name__)


class AbstractModule:

    """This class serves as a basis for all NITE modules."""

    @property
    def NITE(self):
        """Return NITE."""
        return self._NITE

    @NITE.setter
    def NITE(self, value):
        """Set NITE."""
        self._NITE = value

    def start(self):
        """Start the module.

        This is an abstract method, you should implement your own.

        """
        raise NotImplementedError('All derivatives of `AbstractModule` must implement a `start` method.')

    def stop(self):
        """Stop the module.

        This is an abstract method, you should implement your own.

        """
        raise NotImplementedError('All derivatives of `AbstractModule` must implement a `stop` method.')

    def __init__(self, NITE):
        """Construct an instance of this module."""
        self.NITE = NITE


class ModuleManager:

    """The ModuleManager manages the loading, unloading, etc. of modules."""

    @property
    def NITE(self):
        """Return NITE."""
        return self._NITE

    @NITE.setter
    def NITE(self, value):
        """Set NITE."""
        self._NITE = value

    @property
    def modules(self):
        """Return modules."""
        return self._modules

    @modules.setter
    def modules(self, value):
        """Set modules."""
        self._modules = value

    def load_single(self, identifier):
        """Load a module by its identifier."""
        logger.debug('Attempting to load module "%s"', identifier)

        for entry_point in iter_entry_points(group='nite.modules', name=identifier):
            self.modules[identifier] = entry_point.load()(self.NITE)

        logger.debug('Module "%s" loaded', identifier)

    def unload_single(self, identifier):
        """Unload a module by its identifier."""
        logger.debug('Unloading module "%s"', identifier)

        # We need to remove the module from the python interpreter in order for live codebase updates to work.
        sys.modules.pop(self.modules[identifier].__module__)

        del self.modules[identifier]
        self.modules.pop("", None)
        self.modules.pop(None, None)

        logger.debug('Unloaded module "%s"', identifier)

    def load(self):
        """Load all modules."""
        for entry_point in iter_entry_points(group='nite.modules'):
            self.load_single(entry_point.name)

    def unload(self):
        """Unload all modules."""
        # We need to copy the list of identifiers, because unloading a module removed it from the modules dict
        identifiers = list(self.modules.keys())
        for identifier in identifiers:
            self.unload_single(identifier)

    def start_single(self, identifier):
        """Start a module by its identifier."""
        logger.debug('Starting module "%s"', identifier)
        self.modules[identifier].start()
        logger.debug('Module "%s" started', identifier)

    def stop_single(self, identifier):
        """Stop a module by its identifier."""
        logger.debug('Stopping module "%s"', identifier)
        self.modules[identifier].stop()
        logger.debug('Module "%s" stopped', identifier)

    def start(self):
        """Start all modules."""
        self.load()

        for identifier in self.modules.keys():
            self.start_single(identifier)

    def stop(self):
        """Stop all modules."""
        for identifier in self.modules.keys():
            self.stop_single(identifier)

        self.unload()

    def __init__(self, NITE):
        """Constructor."""
        self.NITE = NITE
        self.modules = {}
        logger.debug('Module manager initialized')
