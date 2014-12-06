"""Queue module."""
import msgpack
import logging
import socket
import re
import amqp.connection as amqp
from amqp.basic_message import Message
from nite.event import EventDemographic
from nite.util import get_module_attr, instantiate


logger = logging.getLogger(__name__)


class QueueConnectors:

    """This class helps map queue connectors to their identifiers."""

    amqp = ['nite.queue', 'AmqpQueueConnector']


def create_connector(type, events, config=None):
    """Initialize and return connector to a queue type."""
    # If the extension isn't mapped at all, throw an error.
    if not hasattr(QueueConnectors, type):
        raise Exception('A queue with the type "%s" can\'t be connected to!' % type)

    # Fetch loader data
    loader_data = getattr(QueueConnectors, type)

    # Instantiate the class with our args
    return instantiate(loader_data[0], loader_data[1], events, **config)


class AbstractQueueConnector:

    """This class provides an easy way to interface with various message queueing implementations.

    It handles connecting, disconnecting, communication and the like.

    """

    @property
    def node_identifier(self):
        """Return node identifier."""
        return self._node_identifier

    @node_identifier.setter
    def node_identifier(self, value):
        """Set node identifier."""
        self._node_identifier = value

    @property
    def events(self):
        """Return event manager."""
        return self._events

    @events.setter
    def events(self, value):
        """Set event manager."""
        self._events = value

    def stop(self):
        """Close all connections to the queue and perhaps perform some cleanup.

        This is an abstract method. You shoudld implement your own.

        """
        raise NotImplementedError(
            'All (indirect) derivatives of `AbstractQueueConnector` must implement a `stop` method.')

    def start(self):
        """Initialize connections to the queue and perform some warmup.

        This is an abstract method. You should implement your own.

        """
        raise NotImplementedError(
            'All (indirect) derivatives of `AbstractQueueConnector` must implement an `start` method.')

    def publish(self, event, demographic, reply_event):
        """Publish an event.

        This method should be called by the event manager.
        It should never have to be called manually.

        This is an abstract method. You should implement your own.

        """
        raise NotImplementedError(
            'All (indirect) derivatives of `AbstractQueueConnector` must implement a `publish` method.')

    def fetch(self):
        """Fetch events.

        This method should be called by worker processes.
        It should never have to be called manually.

        This is an abstract method. You should implement your own.

        """
        raise NotImplementedError(
            'All (indirect) derivatives of `AbstractQueueConnector` must implement a `fetch` method.')

    def __init__(self, events):
        """Constructor."""
        self.events = events
        self.node_identifier = 'node.%s' % socket.getfqdn()


class AmqpQueueConnector(AbstractQueueConnector):

    """This class provides an easy way to interface with MQs which implement the AMQP protocol."""

    @property
    def connection(self):
        """Return connection."""
        return self._connection

    @connection.setter
    def connection(self, value):
        """Set connection."""
        self._connection = value

    @property
    def channel(self):
        """Return channel."""
        return self._channel

    @channel.setter
    def channel(self, value):
        """Set channel."""
        self._channel = value

    def stop(self):
        """Close connector and clean up."""
        logger.debug('Attempting to stop AMQP connector')

        self.channel.close()
        self.connection.close()

        logger.debug('AMQP connector stopped successfully')

    def start(self, produce_only=False):
        """Initialize connections to queue."""
        logger.debug('Attempting to start AMQP connector')

        self.connection = self.create_connection()
        self.channel = self.create_channel(produce_only=produce_only)

        logger.debug('AMQP connector started successfully')

    def create_connection(self):
        """Create and return a connection to the queue."""
        return amqp.Connection(
            host=self.config['host'],
            userid=self.config['user'],
            password=self.config['password'],
            virtual_host=self.config['virtual_host'],
            connect_timeout=self.config['connect_timeout'],
            ssl=self.config['ssl']
        )

    def create_channel(self, produce_only=False):
        """Create and return a channel to the queue."""
        channel = self.connection.channel()

        if produce_only:
            return channel

        # Set message prefetch count to 1
        # channel.basic_qos(0, 1, 0)

        # Declare or create the exchanges this channel is going to be using
        channel.exchange_declare(
            self.config['exchange_topic'],
            'topic',
            passive=False,
            durable=True,
            auto_delete=False,
            nowait=False,
            arguments=None
        )

        channel.exchange_declare(
            self.config['exchange_fanout'],
            'fanout',
            passive=False,
            durable=True,
            auto_delete=False,
            nowait=False,
            arguments=None
        )

        # Declare node-specific queue
        channel.queue_declare(
            queue=self.node_identifier,
            passive=False,
            durable=True,
            exclusive=False,
            auto_delete=True,
            nowait=False,
            arguments=None
        )

        # Bind node-specific queue to node-specific routing key
        channel.queue_bind(
            queue=self.node_identifier,
            exchange=self.config['exchange_topic'],
            routing_key=self.node_identifier,
            nowait=False,
            arguments=None
        )

        # Loop through events to be bound and declare queues/bind to queues
        for event in self.events.handlers.keys():
            # Declare the event-specific queue to bind to
            channel.queue_declare(
                queue='event.' + event,
                passive=False,
                durable=True,
                exclusive=False,
                auto_delete=False,
                nowait=False,
                arguments=None
            )

            # Bind routing key on event-specific queue
            channel.queue_bind(
                queue='event.' + event,
                exchange=self.config['exchange_topic'],
                routing_key=event,
                nowait=False,
                arguments=None
            )

            # Bind routing key on node-specific queue
            channel.queue_bind(
                queue=self.node_identifier,
                exchange=self.config['exchange_fanout'],
                routing_key='event.' + event,
                nowait=False,
                arguments=None
            )

            # Start consuming from the queue
            channel.basic_consume(
                queue='event.' + event,
                consumer_tag='',
                no_local=False,
                no_ack=False,
                exclusive=False,
                nowait=False,
                callback=self.on_consume,
                arguments=None,
                on_cancel=None
            )

        # Start consuming from the node-specific queue
        channel.basic_consume(
            queue=self.node_identifier,
            consumer_tag='',
            no_local=False,
            no_ack=False,
            exclusive=False,
            nowait=False,
            callback=self.on_consume,
            arguments=None,
            on_cancel=None
        )

        return channel

    def on_consume(self, message):
        """Handle a consumed message."""
        # Unserialize the data received in the message body
        data = msgpack.loads(message.body, encoding='utf-8')
        # Grab the event class by importing it
        matches = re.match(r'^(.*)\.([^\.]+)$', data['event'])
        Event = get_module_attr(matches.group(1), matches.group(2))
        # Recreate the event with the received data
        event = Event.load(data['data'])

        event._source = message.properties['reply_to']
        event._reply_to_uuid = message.properties['correlation_id'] if 'correlation_id' in message.properties else None

        # Have event handled by event manager
        result = self.events.handle(event)

        # ACK or NACK as needed
        tag = message.delivery_info['delivery_tag']
        self.channel.basic_ack(delivery_tag=tag) if result else channel.basic_nack(delivery_tag=tag)

    def publish(self, event, demographic, reply_event):
        """Publish an event onto the queue."""
        routing_key = 'event.' + event['event']

        # If the demographic is not part of "EventDemographic",
        # we should assume EventDemographic is a routing key.
        if demographic not in EventDemographic:
            routing_key = demographic

        # Create the message.
        message = Message(
            body=msgpack.dumps(event, use_bin_type=True),
            message_id=event['data']['_uuid'],
            correlation_id=reply_event.uuid if reply_event else None,
            reply_to=self.node_identifier
        )

        # Determine exchange name
        exchange = self.config['exchange_%s' %  ('fanout' if demographic is EventDemographic.GLOBAL_ALL else 'topic')]

        # Publish the message
        self.channel.basic_publish(
            message,
            exchange=exchange,
            routing_key=routing_key,
            mandatory=False,
            immediate=False
        )

    def fetch(self):
        """Fetch events.

        This method should be called by worker processes.
        It should never have to be called manually.

        """
        try:
            # Try to drain some events
            self.connection.drain_events(0.5)
        except socket.timeout:
            # If we got a timeout, do nothing
            pass

    def __init__(self, events, exchange_fanout, exchange_topic, virtual_host, host, user, password, ssl=False,
        connect_timeout=5):
        """Constructor."""
        super(self.__class__, self).__init__(events=events)
        self.config = locals()
