"""Event module."""
import uuid
import inspect
import logging
from enum import Enum
from datetime import datetime


logger = logging.getLogger(__name__)


class EventDemographic(Enum):

    """Enum for determining which nodes will receive a published event."""

    LOCAL = 1
    GLOBAL_SINGLE = 2
    GLOBAL_ALL = 3


class EventPriority(Enum):

    """Enum for determining in what order event listeners are executed."""

    HIGHEST = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    LOWEST = 5


class EventManager:

    """This class manages event dispatching and handling."""

    @property
    def handlers(self):
        """Return event handlers."""
        return self._handlers

    @handlers.setter
    def handlers(self, value):
        """Set event handlers."""
        self._handlers = value

    @property
    def queue(self):
        """Return queue manager."""
        return self._queue

    @queue.setter
    def queue(self, value):
        """Set queue manager."""
        self._queue = value

    def register(self, event, handler, priority=None):
        """Register a handler for an event with a certain priority.

        If the `event` passed is a class, the class name and module name
        are used as the name of the event to register an event handler
        for. If `event`is not a class however (for instance: a string),
        the value itself will be used as the event name.

        The `handler` should be a reference to a function or method to
        execute during the handling of an event. This handler will be
        called with a single parameter, namely the reconstructed event.

        `priority` should be one of the values of `EventPriority`.
        """
        # If event is a class, use its name as the event name, else use the value
        # of event itself.
        event_name = event.__module__ + '.' + event.__name__ if inspect.isclass(event) else event

        # If no priority is set, default to medium.
        if priority is None:
            priority = EventPriority.MEDIUM

        # If no listeners for this event exist yet, populate the dictionary
        if event_name not in self.handlers:
            self.handlers[event_name] = {
                EventPriority.HIGHEST.value: [],
                EventPriority.HIGH.value: [],
                EventPriority.MEDIUM.value: [],
                EventPriority.LOW.value: [],
                EventPriority.LOWEST.value: []
            }

        # Add the handler to the collection of handlers
        self.handlers[event_name][priority.value].append(handler)
        logger.debug('Registered a new event handler for "%s" with priority "%s"', event_name, priority)

    def trigger(self, event, demographic=EventDemographic.GLOBAL_SINGLE, reply_to_event=None):
        """Trigger an event of type `event` against the chosen demographic.

        If `event` is not a dict and thus an instance of an event, it will be
        prepared for transport using its `dump()` method. If it is already
        a dict however, it will simple be serialized as-is.

        `demographic` determines which, if not all nodes will be eligible for
        handling this event. `demographic` can either be part of the
        `EventDemographic` set of targets, or it can be a _node identifier_.

        *NOTE:* If the demographic passed is `EventDemographic.LOCAL`, meaning
        that only the local node should handle the event at all, the event
        queueing system will be bypassed altogether and the event will be
        passed directly to the local handler.

        If an event instance is passed as `reply_to_event`, the remote node
        will be notified of this and might be able to take special actions in
        the event of receiving a reply.
        """
        event_data = event if isinstance(event, dict) else event.dump()

        if demographic is EventDemographic.LOCAL:
            self.handle(event_data)
        else:
            self.queue.publish(event_data, demographic, reply_to_event)

    def handle(self, event):
        """Handle the passed event."""
        event_name = event.__class__.__module__ + '.' + event.__class__.__name__
        if event_name not in self.handlers:
            # If this exception ever actually gets raised, something is seriously wrong.
            raise Exception('There are no handlers registered for the event "%s"' % event_name)

        # Execute event listeners in descending priority.
        for priority, handlers in self.handlers[event_name].items():
            for handler in handlers:
                handler(event)

        return True

    def __init__(self):
        """Initialize the event manager."""
        self.handlers = {}
        logger.debug('Event manager initialized')


class BaseEvent:

    """This class serves as a basis for all NITE events."""

    @property
    def uuid(self):
        """Return the UUID of this event."""
        return self._uuid

    @property
    def reply_to_uuid(self):
        """Return the UUID of the event this event is a reply to, or None."""
        return self._reply_to_uuid

    @property
    def source(self):
        """Return the node identifier of the source of this event.

        This property should NEVER be set manually. It should only
        be set by the event manager when this event is received by
        a global node.

        """
        return self._source

    @property
    def timestamp(self):
        """Return the timestamp of when the event was created."""
        return self._timestamp

    @property
    def version(self):
        """Return the version of the event."""
        return self._version

    def is_reply(self):
        """Return a boolean indicating whether or not this event is a reply to another event."""
        return self._reply_to_uuid is not None

    def dump(self):
        """Turn this event into plain data.

        Feel free to override this method in a subclass.

        """
        return {
            'event': self.__class__.__module__ + '.' + self.__class__.__name__,
            'data': self.__dict__
        }

    @classmethod
    def load(cls, data):
        """Populate an event from existing data.

        Feel free to override this method in a subclass.

        """
        # Create a new event without calling __init__
        event = cls.__new__(cls)

        # Populate event with data
        for key, value in data.items():
            setattr(event, key, value)

        return event

    def __init__(self):
        """Create and populate the event."""
        self._uuid = uuid.uuid4().hex
        self._timestamp = datetime.utcnow().isoformat()
        self._version = 1
