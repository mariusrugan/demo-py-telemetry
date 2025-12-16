import logging
import os
import random
import socket

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Global configuration from environment variables
OTEL_COLLECTOR_HOST = os.getenv("OTEL_COLLECTOR_HOST", "127.0.0.1")
OTEL_COLLECTOR_PORT = int(os.getenv("OTEL_COLLECTOR_PORT", "4317"))
OTEL_INSECURE = os.getenv("OTEL_INSECURE", "true").lower() == "true"
SERVICE_NAME = os.getenv("SERVICE_NAME", "demo-py-telemetry")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")

def setup_telemetry() -> tuple[TracerProvider, MeterProvider, LoggerProvider]:
    """
    Set up OpenTelemetry logging with a logger provider and OTLP exporter.
    
    Args:
        None

    Returns:
        tracer_provider (TracerProvider): The configured tracer provider.
        meter_provider (MeterProvider): The configured meter provider.
        logger_provider (LoggerProvider): The configured logger provider.
    
    .. _PEP 484:
        https://www.python.org/dev/peps/pep-0484/
    
    """

    # Create a logger provider with service information
    logger_provider = LoggerProvider(
        resource=Resource.create(
            {
                "service.name": SERVICE_NAME,
                "service.instance.id": random.randint(1, 10),
            }
        ),
    )
    set_logger_provider(logger_provider)
    
    # Configure OTLP exporter to send logs to the collector
    exporter = OTLPLogExporter(
        endpoint=f"{OTEL_COLLECTOR_HOST}:{OTEL_COLLECTOR_PORT}",    
        insecure=OTEL_INSECURE,
    )
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    
    # Create and attach an OpenTelemetry handler to the Python root logger
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)

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

    return tracer_provider, meter_provider, logger_provider