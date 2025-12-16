import logging
import logging.config
import os
import string
import sys
import random
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import time

from fastapi import FastAPI, HTTPException, Query, logger
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from typing_extensions import Annotated

from opentelemetry.trace import StatusCode
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler

from setup_otel import setup_telemetry

# Configure OpenTelemetry logging
OTEL_COLLECTOR_HOST = os.getenv("OTEL_COLLECTOR_HOST", "127.0.0.1")
OTEL_COLLECTOR_PORT = int(os.getenv("OTEL_COLLECTOR_PORT", "4317"))
OTEL_INSECURE = os.getenv("OTEL_INSECURE", "true").lower() == "true"
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "randomizer-api")
SERVICE_VERSION = "0.1.0"

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "encoding": "utf-8",
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)-8s] %(name)-12s: %(message)s",
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

# Set up OpenTelemetry telemetry (tracing, metrics, logging)
tracer_provider, meter_provider, logger_provider = setup_telemetry()

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)

tracer = tracer_provider.get_tracer(__name__)
meter = meter_provider.get_meter(__name__)

# Practice The Telemetry
def practice(how_long: int) -> bool:
    """
    This is the practice "The Telemetry" function.

    Args: 
        how_long (int): Defines how to long to practice (in seconds).

    Returns:
        bool: True for successfully completed practice, False otherwise.
    """
    practice_logger = logging.getLogger("yoda.practice")
    practice_logger.setLevel(logging.INFO)
    start_time = time.time()
    try:
        how_long_int = int(how_long)
        practice_logger.info("Starting to practice The Telemetry for %i second(s)", how_long_int)
        while time.time() - start_time < how_long_int:
            next_char = random.choice(string.punctuation)
            practice_logger.info("Practicing... %s", next_char)
            # print(next_char, end="", flush=True)
            time.sleep(0.5)
        practice_logger.info("Done practicing")
    except ValueError as ve:
        practice_logger.error("I need an integer value for the time to practice: %s", ve)
        return False
    except Exception as e:
        practice_logger.error("An unexpected error occurred: %s", e)
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

# # Custom metrics
# random_number_counter = meter.create_counter(
#     name="random_numbers_generated",
#     description="Count of random numbers generated",
#     unit="1",
# )
# random_value_histogram = meter.create_histogram(
#     name="random_value_distribution",
#     description="Distribution of generated random values",
#     unit="1",
# )
# error_counter = meter.create_counter(
#     name="random_errors_total",
#     description="Count of errors in random number generation",
#     unit="1",
# )


# @asynccontextmanager
# async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
#     """Manage application lifecycle for telemetry cleanup."""
#     logger.info("Starting Randomizer API")
#     yield
#     logger.info("Shutting down Randomizer API")
#     tracer_provider.shutdown()
#     meter_provider.shutdown()


# app = FastAPI(
#     title="Randomizer API",
#     description="A simple API for generating random numbers with OTEL telemetry",
#     version=SERVICE_VERSION,
#     lifespan=lifespan,
# )

# FastAPIInstrumentor.instrument_app(app)

# @app.get("/")
# def home() -> dict[str, str]:
#     """Health check endpoint."""
#     return {"message": "Welcome to the Randomizer API"}


# @app.get("/random/{max_value}")
# def get_random_number(max_value: int) -> dict[str, int]:
#     """Generate a random number between 1 and max_value."""
#     with tracer.start_as_current_span("generate_random") as span:
#         try:
#             if max_value < 1:
#                 raise ValueError("max_value must be at least 1")

#             result = random.randint(1, max_value)
#             span.set_attribute("random.max_value", max_value)
#             span.set_attribute("random.result", result)

#             random_number_counter.add(1, {"endpoint": "/random/{max_value}"})
#             random_value_histogram.record(result)

#             logger.info("Generated random number: max=%d, result=%d", max_value, result)
#             return {"max": max_value, "random_number": result}

#         except ValueError as e:
#             span.set_status(StatusCode.ERROR, str(e))
#             span.record_exception(e)
#             error_counter.add(1, {"endpoint": "/random/{max_value}", "error_type": "ValueError"})
#             raise HTTPException(status_code=400, detail=str(e)) from e


# @app.get("/random-between")
# def get_random_number_between(
#     min_value: Annotated[int, Query(
#         title="Minimum Value",
#         description="The minimum random number",
#         ge=1,
#         le=1000,
#     )] = 1,
#     max_value: Annotated[int, Query(
#         title="Maximum Value",
#         description="The maximum random number",
#         ge=1,
#         le=1000,
#     )] = 99,
# ) -> dict[str, int]:
#     """Generate a random number between min_value and max_value."""
#     with tracer.start_as_current_span("generate_random_between") as span:
#         try:
#             span.set_attribute("random.min_value", min_value)
#             span.set_attribute("random.max_value", max_value)

#             if min_value > max_value:
#                 raise ValueError("min_value can't be greater than max_value")

#             result = random.randint(min_value, max_value)
#             span.set_attribute("random.result", result)

#             random_number_counter.add(1, {"endpoint": "/random-between"})
#             random_value_histogram.record(result)

#             logger.info("Generated random: min=%d, max=%d, result=%d", min_value, max_value, result)
#             return {"min": min_value, "max": max_value, "random_number": result}

#         except ValueError as e:
#             span.set_status(StatusCode.ERROR, str(e))
#             span.record_exception(e)
#             error_counter.add(1, {"endpoint": "/random-between", "error_type": "ValueError"})
#             raise HTTPException(status_code=400, detail=str(e)) from e