"""Configures the logging of the application"""

import os.path
import logging
import logging.config

import structlog


from settings import Settings


def configure_logging(settings: Settings):
    # Processors that will apply to all log records, no matter if they were created by stdlib logging or structlog
    shared_processors = [
        # Add structlog context variables to log lines
        structlog.contextvars.merge_contextvars,
        # Add local thread variables to the log lines
        structlog.threadlocal.merge_threadlocal,
        # Adds a timestamp for every log line
        structlog.processors.TimeStamper(fmt="iso"),
        # Add the name of the logger to the record
        structlog.stdlib.add_logger_name,
        # Adds the log level as a parameter of the log line
        structlog.stdlib.add_log_level,
        # Perform old school %-style formatting. on the log msg/event
        structlog.stdlib.PositionalArgumentsFormatter(),
        # Adds parameters about where in the source code the log function called from (file, line...)
        structlog.processors.CallsiteParameterAdder(
            [
                # The name of the function that the log is in
                structlog.processors.CallsiteParameter.FUNC_NAME,
                # The line number of the log
                structlog.processors.CallsiteParameter.LINENO,
            ],
        ),
        # If the log record contains a string in byte format, this will automatically convert it into a utf-8 string
        structlog.processors.UnicodeDecoder(),
    ]

    # Processors that will only apply to records generated by structlog
    structlog_only_processors = [
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    processors = shared_processors + structlog_only_processors

    # Configure structlog logging
    structlog.configure(
        processors=processors,

        # TODO: Explain this parameter
        context_class=structlog.threadlocal.wrap_dict(dict),

        # Defines how the logs will be printed out.
        logger_factory=structlog.stdlib.LoggerFactory(),

        # TODO: Explain this parameter
        wrapper_class=structlog.stdlib.BoundLogger,
    )

    # Configure standard logging module
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            # Format log records into jsons
            "json_formatter": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
                "foreign_pre_chain": shared_processors
            },
            # Format log records into messages intended for the console
            "plain_console": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(sort_keys=True, colors=settings.console_color_logs),
                "foreign_pre_chain": shared_processors
            },
            # Format log records in a key=value format
            "key_value": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.KeyValueRenderer(key_order=['timestamp', 'level', 'event', 'logger']),
                "foreign_pre_chain": shared_processors
            },
        },
        "handlers": {
            # Output logs to console
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "plain_console",
            },
            # Output logs to file in json format
            "json_file": {
                "class": "logging.handlers.WatchedFileHandler",
                "filename": os.path.join(settings.logs_dir, 'json.log'),
                "formatter": "json_formatter",
            },
            # Output logs to file in a simple "key1=value1 key2=value2" format
            "flat_line_file": {
                "class": "logging.handlers.WatchedFileHandler",
                "filename": os.path.join(settings.logs_dir, "flat_line.log"),
                "formatter": "key_value",
            },
        },
        "loggers": {
            # Output all log of level debug or above to the console and to the two formats of log files
            "": {
                "handlers": ["console", "flat_line_file", "json_file"],
                "level": "DEBUG",
            },
        }
    })
