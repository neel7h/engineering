from cast.analysers import log
import logging


def info(message_id, message):
    """
    Send a warning message with given id.
    
    Generally message ids are of the form : SQL-25, HTML-10, PYTH-67, etc...
    
        logger.warning('SQL-25','my message')
    
    :param message_id: str 
    :param message: str
    """
    if _is_embedded():
        log.info(message_id + ': ' + message)        
    else:        
        logging.info(message_id + ': ' + message)

def warning(message_id, message):
    """
    Send a warning message with given id.
    
    Generally message ids are of the form : SQL-25, HTML-10, PYTH-67, etc...
    
        logger.warning('SQL-25','my message')
    
    :param message_id: str 
    :param message: str
    """
    if _is_embedded():
        log.warning(message_id + ': ' + message)
    else:                
        logging.warning(message_id + ': ' + message)
        

def _is_embedded():
    """
    Allow one api that switch to cast.analysers.log or logging
    """
    import sys
    return not sys.executable.endswith('python.exe')
