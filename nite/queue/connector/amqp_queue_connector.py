"""This module contains the `AmqpQueueConnector` class."""
import msgpack
import logging
import socket
import queue
import re
from setproctitle import setproctitle
import amqp.connection as amqp
from amqp.basic_message import Message
from multiprocessing import Value, Queue, Process
from nite.event import EventDemographic
from nite.util import ignore_signals, get_module_attr
from nite.queue.connector import AbstractQueueConnector


logger = logging.getLogger(__name__)


class AmqpQueueConnector(AbstractQueueConnector):

    """This class provides an easy way to interface with MQs which implement the AMQP protocol."""

    @property
    def base_exchange_name(self):
        """Return base_exchange name."""
        return self._base_exchange_name

    @property
    def bound_event_names(self):
        """Return bound event names."""
        return self._bound_event_names

    @property
    def node_identifier(self):
        """Return node identifier."""
        if not hasattr(self, '_node_identifier'):
            self._node_identifier = self.NITE.configuration.get('nite.queue.node_identifier', socket.getfqdn())

        return self._node_identifier

    @property
    def producer_queue(self):
        """Return producer queue."""
        return self._producer_queue

    @property
    def consumer_queue(self):
        """Return consumer queue."""
        return self._consumer_queue

    @property
    def ack_queue(self):
        """Return ack queue."""
        return self._ack_queue

    @property
    def processes_should_terminate(self):
        """Return whether or not processes should terminate."""
        return self._processes_should_terminate

    @property
    def producer_process(self):
        """Return producer process."""
        return self._producer_process

    @property
    def consumer_process(self):
        """Return consumer process."""
        return self._consumer_process

    def close(self):
        """Close connector and clean up."""
        self.processes_should_terminate.value = True
        self.producer_process.join()
        self.consumer_process.join()
        logger.debug('AMQP connector shut down successfully')

    def create_connection(self):
        """Create and return a connection to the queue."""
        return amqp.Connection(
            host=self.NITE.configuration.get('nite.queue.amqp.host'),
            userid=self.NITE.configuration.get('nite.queue.amqp.user'),
            password=self.NITE.configuration.get('nite.queue.amqp.password'),
            virtual_host=self.NITE.configuration.get('nite.queue.amqp.virtual_host'),
            connect_timeout=self.NITE.configuration.get('nite.queue.amqp.connect_timeout', 5),
            ssl=self.NITE.configuration.get('nite.queue.amqp.ssl', False),
        )

    def create_channel(self, connection, is_producer=False):
        """Create and return a channel to the queue."""
        channel = connection.channel()

        # If is_producer is set to True we'll only be using this channel for
        # producing messages, so there's no need to bind to anything.
        if is_producer:
            return channel

        # Set message prefetch count to 1
        # channel.basic_qos(0, 1, 0)

        # Declare or create the exchangeis this channel is going to be using.
        channel.exchange_declare(
            self.base_exchange_name + '_topic',
            'topic',
            passive=False,
            durable=True,
            auto_delete=False,
            nowait=False,
            arguments=None
        )

        channel.exchange_declare(
            self.base_exchange_name + '_fanout',
            'fanout',
            passive=False,
            durable=True,
            auto_delete=False,
            nowait=False,
            arguments=None
        )

        # Declare node-specific queue
        channel.queue_declare(
            queue='node.' + self.node_identifier,
            passive=False,
            durable=True,
            exclusive=False,
            auto_delete=True,
            nowait=False,
            arguments=None
        )

        # Bind node-specific queue to node-specific routing key
        channel.queue_bind(
            queue='node.' + self.node_identifier,
            exchange=self.base_exchange_name + '_topic',
            routing_key='node.' + self.node_identifier,
            nowait=False,
            arguments=None
        )

        # Loop through events to be bound and declare queues/bind to queues
        for bound_event_name in self.bound_event_names:
            # Declare the event-specific queue to bind to
            channel.queue_declare(
                queue='event.' + bound_event_name,
                passive=False,
                durable=True,
                exclusive=False,
                auto_delete=False,
                nowait=False,
                arguments=None
            )

            # Bind routing key on event-specific queue
            channel.queue_bind(
                queue='event.' + bound_event_name,
                exchange=self.base_exchange_name + '_topic',
                routing_key='event.' + bound_event_name,
                nowait=False,
                arguments=None
            )

            # Bind routing key on node-specific queue
            channel.queue_bind(
                queue='node.' + self.node_identifier,
                exchange=self.base_exchange_name + '_fanout',
                routing_key='event.' + bound_event_name,
                nowait=False,
                arguments=None
            )

            # Start consuming from the queue
            channel.basic_consume(
                queue='event.' + bound_event_name,
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
            queue='node.' + self.node_identifier,
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

    def producer_process_logic(self):
        """Logic for the producer process."""
        # Worker processes should ignore certain signals
        ignore_signals()

        # Set process title (for top, ps and the like)
        setproctitle('NITE AMQP Producer')

        connection = self.create_connection()
        channel = self.create_channel(connection, is_producer=True)

        # While the process should not terminate..
        while not self.processes_should_terminate.value:
            try:
                # Try to get an event from the producer queue.
                event_data = self.producer_queue.get(block=True, timeout=0.1)

                routing_key = 'event.' + event_data[0]['event']

                # If the demographic is not part of "EventDemographic",
                # we should assume EventDemographic is part of a routing key.
                if event_data[1] not in EventDemographic.reverse_mapping:
                    routing_key = 'node.' + event_data[1]

                # Create the message.
                message = Message(
                    body=msgpack.dumps(event_data[0], use_bin_type=True),
                    message_id=event_data[0]['data']['_uuid'],
                    correlation_id=event_data[2].uuid if event_data[2] else None,
                    reply_to='node.' + self.node_identifier
                )

                # Determine exchange name.
                exchange_name_suffix = '_fanout' if event_data[1] is EventDemographic.GLOBAL_ALL else '_topic'
                exchange_name = self.base_exchange_name + exchange_name_suffix

                # Publish the message
                channel.basic_publish(
                    message,
                    exchange=exchange_name,
                    routing_key=routing_key,
                    mandatory=False,
                    immediate=False
                )
            except queue.Empty:
                # If the queue was empty, simply try again.
                pass

        channel.close()
        connection.close()

    def consumer_process_logic(self):
        """Logic for the producer process."""
        # Worker processes should ignore certain signals
        ignore_signals()

        # Set process title (for top, ps and the like)
        setproctitle('NITE AMQP Consumer')

        connection = self.create_connection()
        channel = self.create_channel(connection)

        # While the process should not terminate..
        while not self.processes_should_terminate.value:
            # If there are messsages for us to ack, do that first.
            try:
                while True:
                    delivery_tag = self.ack_queue.get(block=False)
                    channel.basic_ack(delivery_tag=delivery_tag)
            except queue.Empty:
                pass

            try:
                # Try to drain some events
                connection.drain_events(0.1)
            except socket.timeout:
                # If we got a timeout, try again
                pass

        channel.close()
        connection.close()

    def spawn_producer_process(self):
        """Spawn a dedicated producer process."""
        self._producer_process = Process(
            name='PRODUCER',
            daemon=True,
            args=(),
            target=self.producer_process_logic
        )

    def spawn_consumer_process(self):
        """Spawn a dedicated consumer process."""
        self._consumer_process = Process(
            name='CONSUMER',
            daemon=True,
            args=(),
            target=self.consumer_process_logic
        )

    def initialize(self):
        """Initialize the connection to the queue and define exchange/queues."""
        self._base_exchange_name = self.NITE.configuration.get('nite.queue.amqp.exchange_name')
        self._bound_event_names = []
        self._processes_should_terminate = Value('b', False)
        self._producer_queue = Queue()
        self._consumer_queue = Queue()
        self._ack_queue = Queue()

        logger.debug('AMQP queue connector initialized')

    def start(self):
        """Spawn and start the producer and consumer processes."""
        self.spawn_producer_process()
        self.spawn_consumer_process()
        self.producer_process.start()
        self.consumer_process.start()

    def register_event_hook(self, event):
        """Register a hook for a certain event.

        If this method is triggered by the queue manager, it means the first event listener has
        been registered for the specified event.

        This method is only called when the first event listener is registered for this specific
        event, regardless of its priority.

        """
        self.bound_event_names.append(event)
        logger.debug('Event hook registered for event "%s"' % event)

    def on_consume(self, message):
        """Handle a consumed message by turning it into an event and pushing it onto the consumer queue."""
        # Unserialize the data received in the message body
        data = msgpack.loads(message.body, encoding='utf-8')
        # Grab the event class by importing it
        matches = re.match(r'^(.*)\.([^\.]+)$', data['event'])
        Event = get_module_attr(matches.group(1), matches.group(2))
        # Recreate the event with the received data
        event = Event.load(data['data'])

        event._source = message.properties['reply_to'].replace('node.', '')
        event._reply_to_uuid = message.properties['correlation_id'] if 'correlation_id' in message.properties else None
        self.consumer_queue.put([event, message.delivery_info['delivery_tag']])

    def publish_event(self, event, demographic, reply_to_event):
        """Publish an event by pushing it onto the producer queue."""
        self.producer_queue.put([event, demographic, reply_to_event])

    def fetch_events(self, process_should_terminate):
        """Fetch events.

        This method should be called by worker processes.
        It should never have to be called manually.

        """
        while not process_should_terminate.value:
            try:
                # Try to grab an event from the consumer queue.
                event_data = self.consumer_queue.get(block=True, timeout=0.1)

                # Handle our event.
                self.NITE.event_manager.handle_event(event_data[0])

                # Add the delivery tag onto the ack queue.
                self.ack_queue.put(event_data[1])
            except queue.Empty:
                pass
