"""Worker module."""
import logging
import multiprocessing
from setproctitle import setproctitle
from nite.util import ignore_signals


logger = logging.getLogger(__name__)


class Worker(multiprocessing.Process):

    """Worker process class."""

    @property
    def NITE(self):
        """Return NITE."""
        return self._NITE

    @property
    def queue(self):
        """Return queue."""
        return self._queue

    @property
    def process_should_terminate(self):
        """Return whether the worker process should terminate."""
        return self._process_should_terminate

    def __init__(self, NITE, queue, process_should_terminate, name, daemon):
        """Instantiate the worker process."""
        super(Worker, self).__init__(name=name, daemon=daemon)
        self._NITE = NITE
        self._queue = queue
        self._process_should_terminate = process_should_terminate

    def run(self):
        """Main worker function of worker process."""
        # Worker processes should ignore certain signals
        ignore_signals()

        # Set process title (for top, ps and the like)
        setproctitle(self.name)

        # While the process doesn't have to terminate
        while not self.process_should_terminate.value:
            # Fetch and handle events
            self.NITE.queue_connector.fetch_events(self.process_should_terminate)


class WorkerManager:

    """This class manages worker processes."""

    @property
    def NITE(self):
        """Return NITE."""
        return self._NITE

    @property
    def processes(self):
        """Return processes."""
        return self._processes

    @property
    def queue(self):
        """Return queue."""
        return self._queue

    @property
    def processes_should_terminate(self):
        """Return whether or not processes should terminate."""
        return self._processes_should_terminate

    def initialize(self):
        """Initialize the worker manager."""
        self._processes = []
        self._processes_should_terminate = multiprocessing.Value('b', False)
        self._queue = multiprocessing.Queue()

        # Determine correct worker process count
        worker_count = self.NITE.configuration.get('nite.event.worker_processes', multiprocessing.cpu_count())

        # Start spawning individual processes
        for i in range(0, worker_count):
            process = Worker(
                NITE=self.NITE,
                queue=self.queue,
                process_should_terminate=self.processes_should_terminate,
                name='NITE Worker Process #%i' % i,
                daemon=True
            )

            process.start()
            self.processes.append(process)

        logger.info('%s worker process(es) started', worker_count)

    def close(self):
        """Shut down the worker manager."""
        # Tell worker processes that we want them to terminate.
        self._processes_should_terminate.value = True

        # Actually start terminating and joining processes
        for process in self.processes:
            process.join()

    def __init__(self, NITE):
        """Instantiate the worker manager."""
        self._NITE = NITE
        self.initialize()
        logging.debug('Worker manager initialized')
