"""Main module."""
import click
import atexit
import os
import signal
import sys
import time
from logging import getLogger
from select import select
from ballercfg import ConfigurationManager

from nite.util import ensure_dir
from nite.queue import create_connector
from nite.logging import configure_logging
from nite.event import EventManager
from nite.worker import WorkerManager
from nite.module import ModuleManager


logger = getLogger(__name__)


def show_version(ctx, value):
    """Print version information and exit."""
    if not value:
        return

    print('NITE (Nigh Impervious Task Executor) 0.0.1 by Kalman Olah')
    ctx.exit()


@click.command()
@click.option('--debug', '-d', is_flag=True, help='Show debug output.')
@click.option('--daemonize', is_flag=True, help='Daemonize the process.')
@click.option('--version', '-v', is_flag=True, help='Print version information and exit.',
              callback=show_version, expose_value=False, is_eager=True)
def nite(debug, daemonize):
    """NITE - Nigh Impervious Task Executor."""
    NITECore(locals())


class NITECore:

    """NITE Core. Handles all of the magic."""

    @property
    def options(self):
        """Return a dict containing runtime options."""
        return self._options

    @options.setter
    def options(self, value):
        """Set runtime options."""
        self._options = value

    @property
    def config(self):
        """Return a dict containing application configuration."""
        return self._config

    @config.setter
    def config(self, value):
        """Set application configuration."""
        self._config = value

    @property
    def queue(self):
        """Return the queue interface."""
        return self._queue

    @queue.setter
    def queue(self, value):
        """Set the queue interface."""
        self._queue = value

    @property
    def events(self):
        """Return the event manager."""
        return self._events

    @events.setter
    def events(self, value):
        """Set the event manager."""
        self._events = value

    @property
    def modules(self):
        """Return the module manager."""
        return self._modules

    @modules.setter
    def modules(self, value):
        """Set the module manager."""
        self._modules = value

    @property
    def workers(self):
        """Return the worker manager."""
        return self._workers

    @workers.setter
    def workers(self, value):
        """Set the worker manager."""
        self._workers = value

    def start(self):
        """Start."""
        logger.info('Attempting to start')
        self.options['stopping'] = False

        # Load configuration
        self.config = ConfigurationManager.load(['config/*', os.path.expanduser('~') + '/.nite/config/*',
            '/etc/nite/config/*'])

        # Properly set up the logger using values from the configuration
        configure_logging(self.config.get('nite.logging'), debug=self.options['debug'])

        # Initialize event manager
        self.events = EventManager()

        # Initialize queue manager
        queue_type = self.config.get('nite.queue.type', 'amqp')
        self.queue = create_connector(type=queue_type, config=self.config.get('nite.queue.%s' % queue_type),
            events=self.events)

        # Add queue manager reference to event manager
        self.events.queue = self.queue

        # Initialize module manager
        self.modules = ModuleManager(self)
        self.modules.start()

        # Start worker processes
        self.workers = WorkerManager(queue=self.queue, worker_count=self.config.get('nite.event.worker_processes'))
        self.workers.start()

        # Start produce-only queue for use by modules
        self.queue.start(produce_only=True)

        logger.info('Started successfully')

        # Take commands from STDIN
        self.command_loop()

    def stop(self):
        """Stop NITE."""
        logger.info('Attempting to stop')
        self.options['stopping'] = True

        self.queue.stop()
        self.workers.stop()
        self.modules.stop()

        logger.info('Stopped successfully')

    def command_loop(self):
        """Loop for accepting commands from standard input."""
        from nite.command import CommandEvent

        while not self.options['stopping']:
            has_input = False

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
            self.events.handle(command_event)

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
        logger.debug('Received signal %s' % sig)

        if sig is signal.SIGHUP:
            self.stop()
            self.start()
        else:
            self.stop()

    def register_signal_handlers(self):
        """Register signal handlers for this process."""
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGHUP, self.handle_signal)

    def __init__(self, options):
        """Constructor."""
        # Set default options
        self.options = options

        # Apply default logging configuration
        configure_logging(debug=self.options['debug'])

        # Set correct working directory
        os.chdir(os.path.dirname(os.path.dirname(__file__)))

        # Register signal handlers
        self.register_signal_handlers()
        #atexit.register(self.stop)

        # Daemonize if needed
        if self.options['daemonize']:
            self.daemonize_process()

        # Start application
        self.start()
