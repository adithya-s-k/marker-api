import logging
import logging.config
from marker.settings import Settings

def configure_logging():
    settings = Settings()
    
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            },
        },
        'handlers': {
            'default': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
            },
            'file': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': settings.LOG_FILE,
                'maxBytes': 10485760,
                'backupCount': 3,
                'formatter': 'standard',
            },
        },
        'loggers': {
            '': {
                'handlers': ['default', 'file'],
                'level': 'DEBUG',
                'propagate': True
            },
        }
    }

    logging.config.dictConfig(logging_config)
