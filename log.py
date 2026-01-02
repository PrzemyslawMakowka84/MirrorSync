import logging

class Log:
    def __init__(self, path_to_log_file: str):
        self.__log = logging.getLogger(__name__)
        self.__log.setLevel(logging.DEBUG)
        self.__log.handlers.clear()

        # formater
        console_formater = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",)
        file_formater = logging.Formatter(
            "%(asctime)s%(msecs)03d  - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # log handlers
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(path_to_log_file)

        # set formater
        console_handler.setFormatter(console_formater)
        file_handler.setFormatter(file_formater)

        self.__log.addHandler(console_handler)
        self.__log.addHandler(file_handler)

    # logging
    def debug(self, msg):
            self.__log.debug(msg)

    def info(self, msg):
            self.__log.info(msg)

    def warning(self, msg):
        self.__log.warning(msg)

    def error(self, msg):
        self.__log.error(msg)

