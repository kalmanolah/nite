"""Queue module."""
from nite.util import instantiate
from nite.queue.connector import QueueConnectors


def create_connector(NITE):
    """Initialize and return connector to a queue type."""
    queue_type = NITE.configuration.get('nite.queue.type', 'amqp')

    # If the extension isn't mapped at all, throw an error.
    if not hasattr(QueueConnectors, queue_type):
        raise Exception('A queue with the type "%s" can\'t be connected to!' % queue_type)

    # Fetch loader data
    loader_data = getattr(QueueConnectors, queue_type)

    # Instantiate the class with our args
    connector = instantiate(loader_data[0], loader_data[1], NITE)

    # Initialize connector
    connector.initialize()

    return connector
