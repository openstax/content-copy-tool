import json
import logging
"""
This file contains some basic utility functions for the content-copy-tool.
Functions relate to tool setup, selenium, and I/O.
"""

def init_logger(filename):
    """
    Initializes and returns a basic logger to the specified filename.
    """
    logger = logging.getLogger('content-copy')
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(filename)
    file_formatter = logging.Formatter('"%(asctime)s - %(name)s - %(levelname)s - %(message)s"')
    console_formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(console_formatter)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    # logger.captureWarnings(True)
    return logger

def login(driver, credentials):
    """
    A utility function to log into a cnx site with the specified credentials.
    Accepts a driver that has been navigated to the home page of a cnx site and
    enters the credentials and clicks the submit button.

    Arguments:
        driver - the selenium webdriver running the test.
        credentials - a string of the username:password to log in with

    Output:
        None
    """
    username = credentials[:str.index(credentials, ':')] # before the colon
    password = credentials[str.index(credentials, ':')+1:] # after the 1st colon
    authKey = driver.find_element_by_id('__ac_name')
    authKey.send_keys(username)
    pw = driver.find_element_by_id('__ac_password')
    pw.send_keys(password)
    signin = driver.find_element_by_name('submit')
    signin.click()

def parse_json(input):
    """ Returns the parsed json input """
    return json.load(open(input))


class CustomError(Exception):
    def __init__(self, arg):
        self.msg = arg