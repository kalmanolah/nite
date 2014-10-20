"""Logging module."""
import time
from nite.util import enum

"""Standard logging levels."""
LogLevel = enum(
    'DEBUG',
    'INFO',
    'ANNOUNCE',
    'WARNING',
    'ERROR'
)


class LogColors:

    """This class contains ANSI console colors."""

    ANNOUNCE = '\033[95m'
    DEBUG = '\033[94m'
    INFO = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    CLEAR = '\033[0m'


class Logger:

    """Logger class. Does logging."""

    @property
    def queued_logs(self):
        """Return queued logs."""
        return self._queued_logs

    @queued_logs.setter
    def queued_logs(self, value):
        """Set queued logs."""
        self._queued_logs = value

    @property
    def min_loglevel(self):
        """Return min loglevel."""
        return self._min_loglevel

    @min_loglevel.setter
    def min_loglevel(self, value=None):
        """Set min loglevel."""
        if value is None:
            value = LogLevel.INFO

        self._min_loglevel = value
        self.debug('Set the minimum loglevel for the logger to "%s"' % LogLevel.reverse_mapping[value])

    @property
    def date_format(self):
        """Return date format."""
        return self._date_format

    @date_format.setter
    def date_format(self, value=None):
        """Set the date format to be used while logging.

        If the format passed is `None`, the date format is set to
        `%Y-%m-%d %H:%M:%S`. You can use the formatting found at
        `http://docs.python.org/3/library/time.html#time.strftime`.

        """
        if not value:
            value = '%Y-%m-%d %H:%M:%S'

        self._date_format = value
        self.debug('Set the date format for the logger to "%s"' % value)

    @property
    def log_format(self):
        """Return log format."""
        return self._log_format

    @log_format.setter
    def log_format(self, value=None):
        """Set the log format to be used while logging.

        If the format passed is `None`, the log format is set to `[{0}][{1}] {2}`.

        """
        if not value:
            value = '[{0}][{1}] {2}'

        self._log_format = value
        self.debug('Set the log format for the logger to "%s"' % value)

    def log(self, string, level=None):
        """Center logging method.

        Should never have to be called directly. If no
        LogLevel is passed, it will default to the `Logger` instance's `min_loglevel`.

        """
        # If the logger has not been initialized yet, queue the logging and return.
        if not hasattr(self, 'initialized'):
            self.queued_logs.append([string, level])
            return

        if self.queued_logs:
            queued_logs = self.queued_logs[:]
            self.queued_logs = []
            for queued_log in queued_logs:
                self.log(queued_log[0], queued_log[1])

        if level is None:
            level = self.min_loglevel
        elif level < self.min_loglevel:
            return

        reverse_level = LogLevel.reverse_mapping[level]

        output = self.log_format.format(
            time.strftime(self.date_format),
            reverse_level.ljust(8),
            string
        )

        output = getattr(LogColors, reverse_level) + output + LogColors.CLEAR
        print(output)

    def debug(self, string):
        """Log a string with LogLevel DEBUG."""
        self.log(string, LogLevel.DEBUG)

    def info(self, string):
        """Log a string with LogLevel INFO."""
        self.log(string, LogLevel.INFO)

    def announce(self, string):
        """Log a string with LogLevel ANNOUNCE."""
        self.log(string, LogLevel.ANNOUNCE)

    def warning(self, string):
        """Log a string with LogLevel WARNING."""
        self.log(string, LogLevel.WARNING)

    def error(self, string):
        """Log a string with LogLevel ERROR."""
        self.log(string, LogLevel.ERROR)

    def __init__(self):
        """Constructor."""
        self.queued_logs = []

    def initialize(self, min_loglevel=None, date_format=None, log_format=None):
        """
        Initialize the logger.

        If no minimum loglevel is passed, the minimum loglevel is set
        to INFO. This means that, by default, all strings logged with
        LogLevel DEBUG are not logged at all.

        If no date format is passed, the date format is set to
        `%Y-%m-%d %H:%M:%S`. You can use the formatting found at
        `http://docs.python.org/3/library/time.html#time.strftime`.

        If no log format is passed, the log format is set to
        `[{0}][{1}] {2}`.

        """
        self.date_format = date_format
        self.min_loglevel = min_loglevel
        self.log_format = log_format

        self.initialized = True

        self.debug(
            'Logger started [min_loglevel=%s, date_format=%s, log_format=%s]' %
            (
                LogLevel.reverse_mapping[self.min_loglevel],
                self.date_format,
                self.log_format
            )
        )

    def close(self):
        """Close the logger."""
