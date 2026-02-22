import logging

FORMAT = '%(asctime)s: %(message)s'
logging.basicConfig(format=FORMAT)

class Logger(object):
    __instance = None
    DISABLED = True

    def __init__(self):
            if Logger.__instance is None:
                self.logger = logging.getLogger('QuantumNetLogger')
                self.logger.setLevel(logging.DEBUG)
                Logger.__instance = self
            else:
                raise Exception('Esta é uma classe singleton')

    def get_instance():
        if Logger.__instance is None:
            Logger()
        return Logger.__instance

    def activate(self):
        Logger.DISABLED = False
    
    def warn(self, message):
        if not Logger.DISABLED:
            self.logger.warning(message)

    def error(self, message):
        if not Logger.DISABLED:
            self.logger.error(message)

    def log(self, message):
        if not Logger.DISABLED:
            self.logger.info(message)

    def debug(self, message):
        if not Logger.DISABLED:
            self.logger.debug(message)