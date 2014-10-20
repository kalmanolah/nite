"""Module module."""
import glob
import os
import sys
from ballercfg import ConfigurationManager
from nite.logging import LogLevel


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

    def log(self, string, level=LogLevel.INFO):
        """Log a string with a loglevel."""
        self.NITE.logger.log("[%s] %s" % (self.metadata.get('name'), string), level)

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

    @property
    def modules(self):
        """Return modules."""
        return self._modules

    @property
    def module_identifiers(self):
        """Return module identifiers."""
        return self._module_identifiers

    @property
    def module_metadata(self):
        """Return module metadata."""
        return self._module_metadata

    @property
    def module_paths(self):
        """Return module paths."""
        return self._module_paths

    @property
    def module_modules(self):
        """Return module modules."""
        return self._module_modules

    def refresh_module_list(self):
        """Refresh module list and metadata."""
        paths = ['modules/*', os.path.expanduser('~') + '/.nite/modules/*', '/etc/nite/modules/*']
        self._module_identifiers = []
        self._module_metadata = {}
        self._module_paths = {}
        dirs = []

        for path in paths:
            self.NITE.logger.debug('Loading modules matching "%s"' % path)
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

    def load(self, module_identifier):
        """Load a module by its identifier."""
        # If this module already exists in self.modules, it does not
        # need to be loaded.
        if module_identifier in self.modules:
            return

        self.NITE.logger.debug('Loading module "%s"' % module_identifier)
        metadata = self.module_metadata[module_identifier]

        # If the module has dependencies, try load those modules first.
        if metadata.get('dependencies'):
            for dependency in metadata.get('dependencies'):
                self.load(dependency)

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

    def unload(self, module_identifier):
        """Unload a module by its identifier."""
        self.NITE.logger.debug('Unloading module "%s"' % module_identifier)

        del self.modules[module_identifier]
        self.modules.pop("", None)
        self.modules.pop(None, None)

        # We need to remove the module from the python interpreter in order for live codebase updates to work.
        sys.modules.pop(self.module_modules[module_identifier].__name__)
        del self.module_modules[module_identifier]
        self.module_modules.pop("", None)
        self.module_modules.pop(None, None)

    def load_all(self):
        """Load all modules."""
        for module in self.module_identifiers:
            self.load(module)

    def unload_all(self):
        """Unload all modules."""
        for module in self.module_identifiers:
            self.unload(module)

    def start(self, module_identifier):
        """Start a module by its identifier."""
        module = self.modules[module_identifier]

        self.NITE.logger.debug('Starting module "%s"' % module_identifier)
        module.start()
        self.NITE.logger.debug('Module "%s" started' % module_identifier)

    def stop(self, module_identifier):
        """Stop a module by its identifier."""
        module = self.modules[module_identifier]

        self.NITE.logger.debug('Stopping module "%s"' % module_identifier)
        module.stop()
        self.NITE.logger.debug('Module "%s" stopped' % module_identifier)

    def start_all(self):
        """Start all modules."""
        for module in self.module_identifiers:
            self.start(module)

    def stop_all(self):
        """Stop all modules."""
        for module in self.module_identifiers:
            self.stop(module)

    def __init__(self, NITE):
        """Initialize module manager."""
        self._NITE = NITE

        # Initialize module variables.
        self._modules = {}
        self._module_modules = {}
        self.refresh_module_list()

        self.NITE.logger.debug('Module manager initialized')
