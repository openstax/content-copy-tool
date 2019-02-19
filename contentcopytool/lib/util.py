import json
import logging
import re as regex
import signal
"""
This file contains some basic utility functions for the content-copy-tool.
Functions relate to tool setup, selenium, and I/O.
"""

def init_logger(filename):
    """
    Initializes and returns a basic logger to the specified filename.
    """
    logger = logging.getLogger('content-copy')
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(filename)

    file_formatter = ColorStrippingFormatter('"%(asctime)s - %(name)s - %(levelname)s - %(message)s"')
    console_formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")

    console_handler.setFormatter(console_formatter)
    file_handler.setFormatter(file_formatter)

    console_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.DEBUG)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger

class ColorStrippingFormatter(logging.Formatter):
    def format(self, record):
        record.msg = self.remove_color_codes(record.msg)
        return super(ColorStrippingFormatter, self).format(record)

    def remove_color_codes(self, msg):
        return regex.sub(r'\033\[\d*m', "", msg)

def parse_json(input):
    """ Returns the parsed json input """
    return json.load(open(input))


class CCTError(Exception):
    def __init__(self, arg):
        self.msg = arg


class SkipSignal(Exception):
    def __init__(self, arg):
        self.msg = arg


class TerminateError(Exception):
    def __init__(self, arg):
        self.msg = arg

def handle_user_skip(signal, frame):
    raise SkipSignal("Skip Signaled")

def handle_terminate(signal, frame):
    raise TerminateError("Terminate Signaled")
