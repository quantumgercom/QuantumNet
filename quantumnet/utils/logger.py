import logging
from datetime import datetime
from ..exceptions import SingletonError


class Logger(object):
    __instance = None

    def __init__(self):
        if Logger.__instance is None:
            self.logger = logging.getLogger('QuantumNetLogger')
            self.logger.handlers.clear()
            self.logger.addHandler(logging.NullHandler())
            self.logger.setLevel(logging.DEBUG)
            Logger.__instance = self
        else:
            raise SingletonError('This is a singleton class')

    def get_instance():
        if Logger.__instance is None:
            Logger()
        return Logger.__instance

    def activate(self, level='INFO', console=False, file_log=True, filename=None):
        self.logger.handlers.clear()

        fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        log_level = getattr(logging, level.upper(), logging.INFO)

        if file_log:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'quantumnet_{timestamp}.log'
            fh = logging.FileHandler(filename, encoding='utf-8')
            fh.setFormatter(fmt)
            fh.setLevel(log_level)
            self.logger.addHandler(fh)

        if console:
            sh = logging.StreamHandler()
            sh.setFormatter(fmt)
            sh.setLevel(log_level)
            self.logger.addHandler(sh)

    def warn(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def log(self, message):
        self.logger.info(message)

    def debug(self, message):
        self.logger.debug(message)
