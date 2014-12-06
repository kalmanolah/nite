"""Module module."""
import glob
import os
import sys
import logging
from ballercfg import ConfigurationManager


logger = logging.getLogger(__name__)


class AbstractModule:

    """This class serves as a basis for all NITE modules."""

    @property
    def NITE(self):
        """Return NITE."""
        return self._NITE

    @property
    def metadata(self):
        """Return metadata."""
        return self._metadata

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

    def __init__(self, NITE, metadata):
        """Construct an instance of this module with some metadata."""
        self._NITE = NITE
        self._metadata = metadata


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

    @property
    def module_identifiers(self):
        """Return module identifiers."""
        return self._module_identifiers

    @module_identifiers.setter
    def module_identifiers(self, value):
        """Set module identifiers."""
        self._module_identifiers = value

    @property
    def module_metadata(self):
        """Return module metadata."""
        return self._module_metadata

    @module_metadata.setter
    def module_metadata(self, value):
        """Set module metadata."""
        self._module_metadata = value

    @property
    def module_paths(self):
        """Return module paths."""
        return self._module_paths

    @module_paths.setter
    def module_paths(self, value):
        """Set module paths."""
        self._module_paths = value

    @property
    def module_modules(self):
        """Return module modules."""
        return self._module_modules

    @module_modules.setter
    def module_modules(self, value):
        """Set module modules."""
        self._module_modules = value

    def refresh_module_list(self):
        """Refresh module list and metadata."""
        paths = ['modules/*', os.path.expanduser('~') + '/.nite/modules/*', '/etc/nite/modules/*']
        self.module_identifiers = []
        self.module_metadata = {}
        self.module_paths = {}
        dirs = []

        for path in paths:
            logger.debug('Loading modules matching "%s"', path)
            entries = glob.glob(path)
            for entry in entries:
                if os.path.isdir(entry):
                    dirs.append(entry)

        for dir in dirs:
            module_path = dir + '/module.*'
            source_path = dir + '/src'

            if not glob.glob(module_path):
                raise IOError('No module file matching "%s" found!' % module_path)

            metadata = ConfigurationManager.load(module_path)
            identifier = metadata.get('identifier', metadata.get('name'))

            self.module_identifiers.append(identifier)
            self.module_metadata[identifier] = metadata
            self.module_paths[identifier] = source_path

    def load_single(self, module_identifier):
        """Load a module by its identifier."""
        # If this module already exists in self.modules, it does not
        # need to be loaded.
        if module_identifier in self.modules:
            return

        logger.debug('Loading module "%s"', module_identifier)
        metadata = self.module_metadata[module_identifier]

        # If the module has dependencies, try load those modules first.
        if metadata.get('dependencies'):
            for dependency in metadata.get('dependencies'):
                self.load_single(dependency)

        # Add the module's src/ folder to python's PYTHONPATH.
        sys.path.insert(0, '%s/%s' % (os.getcwd(), self.module_paths[module_identifier]))

        # The manifest is the module and class we need to instantiate.
        manifest = metadata.get('manifest')

        # Dynamically import the correct module.
        module = __import__(manifest[0], globals(), locals(), manifest[1])
        self.module_modules[module_identifier] = module

        # Grab the main class for the module.
        class_ = getattr(module, manifest[1])

        # Instantiate the module and pass NITE & metadata along.
        instance = class_(self.NITE, metadata)
        self.modules[module_identifier] = instance

    def unload_single(self, module_identifier):
        """Unload a module by its identifier."""
        logger.debug('Unloading module "%s"', module_identifier)

        del self.modules[module_identifier]
        self.modules.pop("", None)
        self.modules.pop(None, None)

        # We need to remove the module from the python interpreter in order for live codebase updates to work.
        sys.modules.pop(self.module_modules[module_identifier].__name__)
        del self.module_modules[module_identifier]
        self.module_modules.pop("", None)
        self.module_modules.pop(None, None)

    def load(self):
        """Load all modules."""
        for module in self.module_identifiers:
            self.load_single(module)

    def unload(self):
        """Unload all modules."""
        for module in self.module_identifiers:
            self.unload_single(module)

    def start_single(self, module_identifier):
        """Start a module by its identifier."""
        module = self.modules[module_identifier]

        logger.debug('Starting module "%s"', module_identifier)
        module.start()
        logger.debug('Module "%s" started', module_identifier)

    def stop_single(self, module_identifier):
        """Stop a module by its identifier."""
        module = self.modules[module_identifier]

        logger.debug('Stopping module "%s"', module_identifier)
        module.stop()
        logger.debug('Module "%s" stopped', module_identifier)

    def start(self):
        """Start all modules."""
        self.load()

        for module in self.module_identifiers:
            self.start_single(module)

    def stop(self):
        """Stop all modules."""
        for module in self.module_identifiers:
            self.stop_single(module)

        self.unload()

    def __init__(self, NITE):
        """Constructor."""
        self.NITE = NITE

        # Initialize module variables.
        self.modules = {}
        self.module_modules = {}
        self.refresh_module_list()

        logger.debug('Module manager initialized')
