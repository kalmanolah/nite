"""Worker module."""
import logging
import multiprocessing
import signal
from setproctitle import setproctitle


logger = logging.getLogger(__name__)


class Worker(multiprocessing.Process):

    """Worker process class."""

    @property
    def queue(self):
        """Return queue manager."""
        return self._queue

    @queue.setter
    def queue(self, value):
        """Set queue manager."""
        self._queue = value

    @property
    def terminate(self):
        """Return whether process should terminate."""
        return self._terminate

    @terminate.setter
    def terminate(self, value):
        """Set whether process should terminate."""
        self._terminate = value

    def __init__(self, queue, terminate, name, daemon):
        """Instantiate the worker process."""
        super(self.__class__, self).__init__(name=name, daemon=daemon)
        self.queue = queue
        self.terminate = terminate

    def run(self):
        """Main worker function of worker process."""
        # Worker processes should ignore certain signals
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        # Set process title (for top, ps and the like)
        setproctitle(self.name)

        # Start queue connector
        self.queue.start()

        # While the process doesn't have to terminate
        while not self.terminate.value:
            # Fetch events
            self.queue.fetch()

        # Stop queue connector
        self.queue.stop()


class WorkerManager:

    """This class manages worker processes."""

    @property
    def queue(self):
        """Return queue manager."""
        return self._queue

    @queue.setter
    def queue(self, value):
        """Set queue manager."""
        self._queue = value

    @property
    def worker_count(self):
        """Return worker count."""
        return self._worker_count

    @worker_count.setter
    def worker_count(self, value):
        """Set worker count."""
        self._worker_count = value

    @property
    def processes(self):
        """Return processes."""
        return self._processes

    @processes.setter
    def processes(self, value):
        """Set processes."""
        self._processes = value

    @property
    def terminate(self):
        """Return whether process should terminate."""
        return self._terminate

    @terminate.setter
    def terminate(self, value):
        """Set whether process should terminate."""
        self._terminate = value

    def start(self):
        """Initialize the worker manager."""
        self.processes = []
        self.terminate = multiprocessing.Value('b', False)

        # Start spawning individual processes
        for i in range(0, self.worker_count):
            process = Worker(
                queue=self.queue,
                terminate=self.terminate,
                name='NITE Worker Process #%i' % i,
                daemon=True
            )

            process.start()
            self.processes.append(process)

        logger.info('%s worker process(es) started', self.worker_count)

    def stop(self):
        """Shut down the worker manager."""
        # Tell worker processes that we want them to terminate.
        self.terminate.value = True

        # Actually start terminating and joining processes
        for process in self.processes:
            process.join()

    def __init__(self, queue, worker_count=None):
        """Instantiate the worker manager."""
        self.queue = queue
        self.worker_count = worker_count if worker_count else multiprocessing.cpu_count()
        logging.debug('Worker manager initialized')
