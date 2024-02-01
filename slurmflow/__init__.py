import logging

# Configure package-level logger
logger = logging.getLogger(__name__)
level=logging.INFO
logger.setLevel(level)  # Adjust as needed

# Create handler (e.g., console handler) and add it if not already added
if not logger.handlers:  # Simple check to avoid adding multiple handlers
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

logger.propagate = False  # Prevent messages from being propagated to parent loggers

