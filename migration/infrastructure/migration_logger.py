import logging
import os
from datetime import datetime

class MigrationLogger():

    @staticmethod
    def init() -> logging.Logger:
        log_file_handler = logging.FileHandler(os.path.abspath("logs") + "/migration_%i.log" % int(datetime.now().timestamp()))
        log_file_handler.setLevel(logging.DEBUG)
        log_file_handler.setFormatter(
            logging.Formatter('%(asctime)s|%(levelname)s\t|%(message)s |%(funcName)s in %(filename)s:%(lineno)d',
                                '%Y-%m-%d %H:%M:%S'))

        logger = logging.getLogger()
        logger.addHandler(log_file_handler)
        logger.setLevel(logging.DEBUG)

        return logger