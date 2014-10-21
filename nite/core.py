"""Core module."""
import atexit
import os
import signal
import sys
import time
import logging
from select import select
from ballercfg import ConfigurationManager

from nite.util import ensure_dir, set_working_directory
from nite.queue import create_connector
from nite.logging import configure_logging
from nite.event import EventManager
from nite.worker import WorkerManager
from nite.module import ModuleManager


logger = logging.getLogger(__name__)


class NITECore:

    """NITE Core. Handles all of the magic."""

    @property
    def configuration(self):
        """Return configuration."""
        return self._configuration

    @property
    def text_parser(self):
        """Return text parser."""
        return self._text_parser

    @property
    def queue_connector(self):
        """Return queue connector."""
        return self._queue_connector

    @property
    def module_manager(self):
        """Return module manager."""
        return self._module_manager

    @property
    def event_manager(self):
        """Return event manager."""
        return self._event_manager

    @property
    def worker_manager(self):
        """Return worker manager."""
        return self._worker_manager

    @property
    def debug(self):
        """Return debug."""
        return self._debug

    @property
    def stopping(self):
        """Return stopping."""
        return self._stopping

    @property
    def daemonize(self):
        """Return daemonize."""
        return self._daemonize

    @property
    def daemonized(self):
        """Return daemonized."""
        return self._daemonized

    def start(self):
        """Start NITE."""
        logger.info('Initializing NITE [debug=%s, daemonize=%s]', self.debug, self.daemonize)
        self._stopping = False

        # Register exit handler and set working directory
        atexit.register(self.stop)
        set_working_directory()

        # Load configuration
        self._configuration = ConfigurationManager.load([
            'config/*',
            os.path.expanduser('~') + '/.nite/config/*',
            '/etc/nite/config/*'
        ])

        # Properly set up the logger using values from the configuration
        configure_logging(self.configuration.get('nite.logging'), debug=self.debug)

        # Initialize queue connection
        self._queue_connector = create_connector(self)

        # Initialize event manager
        self._event_manager = EventManager(self)

        # Initialize module manager and load modules
        self._module_manager = ModuleManager(self)
        self.module_manager.load_all()
        self.module_manager.start_all()

        # Actually start queue connector
        self.queue_connector.start()

        # Start worker processes
        self._worker_manager = WorkerManager(self)

        logger.info('NITE initialized successfully')

        # If we're not daemonized, take commands from standard input
        if self.daemonized:
            self.infinite_loop()
        else:
            self.command_loop()

    def stop(self):
        """Stop NITE."""
        logger.info('Stopping NITE')
        self._stopping = True

        # Unregister exit handler (so we don't stop twice)
        atexit.unregister(self.stop)

        self.worker_manager.close()
        self.module_manager.stop_all()
        self.module_manager.unload_all()
        self.queue_connector.close()

        logger.info('NITE stopped successfully')

    def infinite_loop(self):
        """Loop for the sake of looping, so the process doesn't die."""
        while not self._stopping:
            time.sleep(0.1)

    def command_loop(self):
        """Loop for accepting commands from standard input."""
        from nite.command import CommandEvent

        while not self._stopping:
            try:
                has_input, _, _ = select([sys.stdin], [], [], 1)
            except InterruptedError:  # noqa
                pass

            line = None
            if has_input:
                line = sys.stdin.readline().rstrip()

            if not line:
                continue

            # Create a new command event and have it handled
            command_event = CommandEvent(line)
            self.event_manager.handle_event(command_event)

    def daemonize_process(self):
        """Daemonizes.

        Modified code from: http://workaround.cz/daemon-in-python-3/

        """
        # Fork and if we're the parent: exit (1)
        pid = os.fork()
        if pid > 0:
            sys.exit(0)

        # Go solo.
        os.setsid()
        os.umask(0)

        # Fork and if we're the parent: exit (2)
        pid = os.fork()
        if pid > 0:
            sys.exit(0)

        pid = os.getpid()

        logger.info('Sending daemon to background, PID: %s' % pid)
        self._daemonized = True

        # Write the PIDfile and register a function to clean it up
        self._pid_file_path = '/tmp/nite/daemon.pid'
        ensure_dir(os.path.dirname(self._pid_file_path))
        atexit.register(self.delete_pid_file)
        if os.path.exists(self._pid_file_path):
            self.delete_pid_file()
        open(self._pid_file_path, 'w+').write("%s\n" % pid)

        # Set stdout, stderr and stdin to /dev/null
        sys.stdout.flush()
        sys.stderr.flush()

        stdout = open('/dev/null', 'a+')
        stderr = open('/dev/null', 'a+')
        stdin = open('/dev/null', 'r')

        os.dup2(stdout.fileno(), sys.stdout.fileno())
        os.dup2(stderr.fileno(), sys.stderr.fileno())
        os.dup2(stdin.fileno(), sys.stdin.fileno())

    def delete_pid_file(self):
        """Remove the PID file."""
        os.remove(self._pid_file_path)

    def handle_signal(self, sig, frame):
        """Handle a signal sent to this process."""
        self.stop()

        # SIGHUP qualifies as a restart
        if sig is signal.SIGHUP:
            self.start()

    def register_signal_handlers(self):
        """Register signal handlers for this process."""
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGHUP, self.handle_signal)

    def __init__(self, debug=False, daemonize=True):
        """Constructor, all it really does is start NITE indirectly."""
        self._debug = debug
        self._daemonize = daemonize
        self._daemonized = False

        configure_logging(debug=debug)
        self.register_signal_handlers()

        # Daemonize if needed
        if self.daemonize and not self.daemonized:
            self.daemonize_process()

        self.start()
