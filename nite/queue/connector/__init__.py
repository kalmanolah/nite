"""Queue connector module."""


class AbstractQueueConnector:

    """This class provides an easy way to interface with various message queueing implementations.

    It handles connecting, disconnecting, communication and the like.

    """

    @property
    def NITE(self):
        """Return NITE."""
        return self._NITE

    def close(self):
        """Close all connections to the queue and perhaps perform some cleanup.

        This is an abstract method. You shoudld implement your own.

        """
        raise NotImplementedError(
            'All (indirect) derivatives of `AbstractQueueConnector` must implement a `close` method.')

    def initialize(self):
        """Initialize connections to the queue and perform some warmup, perhaps.

        This is an abstract method. You should implement your own.

        """
        raise NotImplementedError(
            'All (indirect) derivatives of `AbstractQueueConnector` must implement an `initialize` method.')

    def start(self):
        """Start connections to the queue and perform some warmup, perhaps.

        This is an abstract method. You should implement your own.

        """
        raise NotImplementedError(
            'All (indirect) derivatives of `AbstractQueueConnector` must implement a `start` method.')

    def register_event_hook(self, event):
        """Register a hook for a certain event.

        If this method is triggered by the queue manager, it means the first event listener has
        been registered for the specified event.

        This method is only called when the first event listener is registered for this specific
        event, regardless of its priority.

        This is an abstract method. You should implement your own.

        """
        raise NotImplementedError(
            'All (indirect) derivatives of `AbstractQueueConnector` must implement a `register_event_hook` method.')

    def publish_event(self, event, demographic, reply_to_event):
        """Publish an event.

        This method should be called by the event manager.
        It should never have to be called manually.

        This is an abstract method. You should implement your own.

        """
        raise NotImplementedError(
            'All (indirect) derivatives of `AbstractQueueConnector` must implement a `publish_event` method.')

    def fetch_events(self, process_should_terminate):
        """Fetch events.

        This method should be called by worker processes.
        It should never have to be called manually.

        This is an abstract method. You should implement your own.

        """
        raise NotImplementedError(
            'All (indirect) derivatives of `AbstractQueueConnector` must implement a `fetch_events` method.')

    def __init__(self, NITE):
        """Construct an instance of this class."""
        self._NITE = NITE


class QueueConnectors:

    """This class helps map queue connectors to their identifiers."""

    amqp = ['nite.queue.connector.amqp_queue_connector', 'AmqpQueueConnector']
