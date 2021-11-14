import logging 
import re
import sty
import os
from src.core.options import options

ATTENTION = 15


class ColorFormatter(logging.Formatter):
    def format(self, record):
        res = super(ColorFormatter, self).format(record)
        if record.levelno >= logging.ERROR:
            res = sty.fg.red + sty.ef.bold + res + sty.rs.all
        elif record.levelno == logging.WARNING:
            res = sty.fg.yellow + res + sty.rs.all
        elif record.levelno == ATTENTION:
            res = sty.fg.green + sty.ef.bold + res + sty.rs.all
        return res

class NoColorFormatter(logging.Formatter):
    def format(self, record):
        try:
            res = super(NoColorFormatter, self).format(record)
        except TimeoutError as err:
            print("logger timeout")
        res = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', res)
        return res

def create_logger(name, output_type="file", level=logging.DEBUG, file_name='run_log.log'):
    """
    we can choose this is a file logger or a console logger
    for now, we hard set the log file name to be run_log.log

    Args:
        name: the name of the logger
        log_type: choose from file or console

    Return:
        the created logger
    """
    logger = logging.getLogger(name)

    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    file_handler = logging.FileHandler(filename=file_name)
    file_handler.setFormatter(NoColorFormatter())
    stream_handler = logging.StreamHandler()
    if os.name == 'nt': # Windows
        stream_handler.setFormatter(NoColorFormatter())
    else:
        stream_handler.setFormatter(ColorFormatter())

    logger.setLevel(level)

    if output_type == "file":
        logger.addHandler(file_handler)
    elif output_type == "console":
        logger.addHandler(stream_handler)

    return logger

class Loggers:
    class __Loggers:
        def __init__(self):
            self.update_loggers()

        def update_loggers(self, base_location="./logs"):
            if not os.path.exists(base_location):
                os.makedirs(base_location)

            if options.print:
                self.main_logger = create_logger("main", output_type='console')
            else:
                self.main_logger = create_logger("main", file_name=os.path.join(base_location, 'main.log'))

            self.print_logger = create_logger("print", output_type='console')
            self.debug_logger = create_logger("debug", file_name=os.path.join(base_location,"debug.log"))
            self.progress_logger = create_logger("progress", file_name=os.path.join(base_location,"progress.log"))
            self.error_logger = create_logger("error", file_name=os.path.join(base_location,"error.log"))
            self.res_logger = create_logger("result", file_name=os.path.join(base_location,"results.log"))
            self.succ_logger = create_logger("success", file_name=os.path.join(base_location,"succ.log"))
            self.stat_logger= create_logger("stat_logger", file_name=os.path.join(base_location,"stat.log"))
            self.detail_logger = create_logger("details", file_name=os.path.join(base_location,"details.log"))
            self.tmp_res_logger = create_logger("result_tmp", file_name=os.path.join(base_location,"results_tmp.log"))
    instance = None
    def __init__(self):
        if not Loggers.instance:
            Loggers.instance = Loggers.__Loggers()
    def __getattr__(self, name):
        return getattr(self.instance, name)
    def __setattr__(self, name):
        return setattr(self.instance, name)

loggers = Loggers()
