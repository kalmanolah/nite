"""Event module."""
import uuid
import inspect
from datetime import datetime
from nite.util import enum


"""
Event demographic.

Enum for determining which nodes will receive a published event.

"""
EventDemographic = enum(
    'LOCAL',
    'GLOBAL_SINGLE',
    'GLOBAL_ALL'
)


"""
Event priority.

Enum for determining in what order event listeners are executed.

"""
EventPriority = enum(
    'HIGHEST',
    'HIGH',
    'MEDIUM',
    'LOW',
    'LOWEST'
)


class EventManager:

    """This class manages event dispatching and handling."""

    @property
    def NITE(self):
        """Return NITE."""
        return self._NITE

    @property
    def event_listeners(self):
        """Return event listeners."""
        return self._event_listeners

    def register_event_listener(self, event, listener, priority=None):
        """Register a listener for an event with a certain priority.

        If the `event` passed is a class, the class name and module name
        are used as the name of the event to register an event listener
        for. If `event`is not a class however (for instance: a string),
        the value itself will be used as the event name.

        The `listener` should be a reference to a function or method to
        execute during the handling of an event. This listener will be
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
        if event_name not in self.event_listeners:
            self.event_listeners[event_name] = {
                EventPriority.HIGHEST: [],
                EventPriority.HIGH: [],
                EventPriority.MEDIUM: [],
                EventPriority.LOW: [],
                EventPriority.LOWEST: []
            }

            # Trigger initial event hook registration via the queue connector
            self.NITE.queue_connector.register_event_hook(event_name)

        # Add the listener to the collection of listeners
        self.event_listeners[event_name][priority].append(listener)

        self.NITE.logger.debug('Registered a new event listener for "%s" with priority "%s"' % (
            event_name,
            EventPriority.reverse_mapping[priority]
        ))

    def trigger_event(self, event, demographic=EventDemographic.GLOBAL_SINGLE, reply_to_event=None):
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
            self.handle_event(event_data)
        else:
            self.NITE.queue_connector.publish_event(event_data, demographic, reply_to_event)

    def handle_event(self, event):
        """Handle the passed event."""
        event_name = event.__class__.__module__ + '.' + event.__class__.__name__
        if event_name not in self.event_listeners:
            # If this exception ever actually gets raised, something is seriously wrong.
            raise Exception('There are no listeners registered for the event "%s"' % event_name)

        # Execute event listeners in descending priority.
        for priority, listeners in self.event_listeners[event_name].items():
            for listener in listeners:
                listener(event)

    def __init__(self, NITE):
        """Initialize the event manager."""
        self._NITE = NITE
        self._event_listeners = {}
        self.NITE.logger.debug('Event manager initialized')


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
