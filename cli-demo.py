"""
Original idea by: 
https://github.com/mhausenblas/ref.otel.help/tree/main/how-to/logs-collection

"""
import logging
import logging.config
import os
import random
import sys
import string
import time
from turtle import tracer
import socket

from grpc import StatusCode
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs.export import ConsoleLogRecordExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.metrics import (
    CallbackOptions,
    Observation,
    get_meter_provider,
    set_meter_provider,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.trace import Status, StatusCode

OTEL_COLLECTOR_HOST = os.getenv("OTEL_COLLECTOR_HOST", "127.0.0.1")
OTEL_COLLECTOR_PORT = int(os.getenv("OTEL_COLLECTOR_PORT", "4317"))
OTEL_INSECURE = os.getenv("OTEL_INSECURE", "true").lower() == "true"

SERVICE_NAME = os.getenv("SERVICE_NAME", "demo-py-telemetry")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "encoding": "utf-8",
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s resource.service.name=%(otelServiceName)s trace_sampled=%(otelTraceSampled)s] - %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    }
}
logging.config.dictConfig(LOGGING_CONFIG)

logger_provider = LoggerProvider(
    resource=Resource.create(
        {
            "service.name": "train-the-telemetry",
            "service.instance.id": os.uname().nodename,
        }
    ),
)
set_logger_provider(logger_provider)

otlp_exporter = OTLPLogExporter(endpoint=f"{OTEL_COLLECTOR_HOST}:{OTEL_COLLECTOR_PORT}", insecure=OTEL_INSECURE)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))

# console_exporter = ConsoleLogRecordExporter()
# logger_provider.add_log_record_processor(BatchLogRecordProcessor(console_exporter))

handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)

"""
Configure OpenTelemetry tracing and metrics.
"""
resource = Resource.create({
    "service.name": SERVICE_NAME,
    "service.version": SERVICE_VERSION,
    "service.instance.id": os.getenv("HOSTNAME", socket.gethostname()),
})

# Tracing
tracer_provider = TracerProvider(resource=resource)
span_exporter = OTLPSpanExporter(endpoint=f"{OTEL_COLLECTOR_HOST}:{OTEL_COLLECTOR_PORT}", insecure=OTEL_INSECURE)
tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
trace.set_tracer_provider(tracer_provider)

# Metrics
metric_exporter = OTLPMetricExporter(endpoint=f"{OTEL_COLLECTOR_HOST}:{OTEL_COLLECTOR_PORT}", insecure=OTEL_INSECURE)
metric_reader = PeriodicExportingMetricReader(
    exporter=metric_exporter,
    export_interval_millis=5000,
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)

# Log correlation - inject trace/span IDs into log records
LoggingInstrumentor().instrument(set_logging_format=True)

tracer = trace.get_tracer(__name__)

meter = get_meter_provider().get_meter("getting-started", "yoda.practice")
counter = meter.create_counter("counter", unit="1", description="Counts things")

# Practice The Telemetry
def practice(how_long):
    """
    This is the practice "The Telemetry" function.

    Args:
        how_long (int): Defines how to long to practice (in seconds).

    Returns:
        bool: True for successfully completed practice, False otherwise.
    """

    with tracer.start_as_current_span("yoda.practice") as span:
        start_time = time.time()

        practice_logger = logging.getLogger("yoda.practice")
        practice_logger.setLevel(logging.INFO)

        span.set_attribute("practice.start_time", start_time)
        span.set_attribute("practice.duration.seconds", how_long)

        try:
            how_long_int = int(how_long)
            counter.add(how_long_int, {"practice": "the-telemetry"})
            
            practice_logger.info("starting to practice The Telemetry for %i second(s)", how_long_int)
            
            while time.time() - start_time < how_long_int:
                next_char = random.choice(string.punctuation)
                # print(next_char, end="", flush=True)
                practice_logger.info("Practicing: %s", next_char)
                time.sleep(0.5)
            
            end_time = time.time()
            practice_logger.info("Done practicing")

            span.set_attribute("practice.end_time", end_time)
            span.set_attribute("counter", how_long_int)

        except ValueError as ve:
            practice_logger.error("I need an integer value for the time to practice: %s", ve)
            return False
        except Exception as e:
            practice_logger.error("An unexpected error occurred: %s", e)
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            return False
        return True

# Main function
def main():
    """
    The main function of the Python program.
    """
    # Attach OTLP handler to root logger
    logging.getLogger().addHandler(handler)
    main_logger = logging.getLogger("yoda.main")
    main_logger.setLevel(logging.INFO)
    if len(sys.argv) < 2:
        main_logger.error("Usage: python %s TIME_TO_PRACTICE_IN_SECONDS", sys.argv[0])
        sys.exit(1)
    result = practice(sys.argv[1])
    main_logger.info("Practicing The Telemetry completed: %s", result)
    logger_provider.shutdown()

# Standard boilerplate calling main() function
if __name__ == "__main__":
    main()