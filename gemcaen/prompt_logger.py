import logging 

logging_level = logging.INFO
logger = logging

logger.basicConfig(format='[{asctime}.{msecs:03.0f}] {levelname} {threadName} - {message}', datefmt='%B %d - %H:%M:%S',level=logging_level,style="{",handlers=[logging.FileHandler("./logs/debug.log"),logging.StreamHandler()])
logger.addLevelName( logger.DEBUG, "\033[1;90m%s\033[1;0m" % logger.getLevelName(logger.DEBUG))
logger.addLevelName( logger.INFO, "\033[1;92m%s\033[1;0m" % logger.getLevelName(logger.INFO))
logger.addLevelName( logger.WARNING, "\033[1;93m%s\033[1;0m" % logger.getLevelName(logger.WARNING))
logger.addLevelName( logger.ERROR, "\033[1;31m%s\033[1;0m" % logger.getLevelName(logger.ERROR))
