import logging

from config import APP_DIR, DEBUG_MODE

logger = logging.getLogger(__name__)

if DEBUG_MODE:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.WARNING)

streamHandler = logging.StreamHandler()
streamHandler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(levelname)s:%(name)s:%(funcName)s:%(lineno)s] %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

