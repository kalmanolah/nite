"""Command module."""
from nite.event import BaseEvent


class CommandEvent(BaseEvent):

    """Event wrapper around an executed command."""

    @property
    def command(self):
        """Return the command this event wraps."""
        return self._command

    @property
    def handled(self):
        """Return a boolean indicating whether or not this command has been handled."""
        return self._handled

    @handled.setter
    def handled(self, value):
        """Set a boolean indicating whether or not this command has been handled."""
        self._handled = value

    def __init__(self, command):
        """Create and populate the event."""
        super(BaseEvent, self).__init__()
        self._command = command
        self.handled = False
