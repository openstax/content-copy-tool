import json
import logging
import datetime
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

def parse_input(input):
    """ Returns the parsed json input """
    return json.load(open(input))

def encode_json(data):
    """ Encodes the given data as json """
    return json.dumps(data, indent=4)

def write_list_to_file(datalist, booktitle):
    """
    Writes the data list to an output file.

    The output file is named: [booktitle].out and the data list may be of
    varying format. Each entry in the list will be written out to the file
    where each element in each entry will be separated by a space character.

    For example:
    [['a', 'b', 'c'], ['d','e'], ['f']]

    will look like:

    a b c
    d e
    f

    """
    filename = booktitle+str(datetime.datetime.now())+'.out'
    file = open(filename, 'w')
    for entry in datalist:
        outstr = str(entry[0])
        for item in entry[1:]:
            outstr += ' '+str(item)
        outstr += '\n'
        file.write(outstr)
    file.close()
    return filename

def record_creation(datalist, args):
    """ Appends a tuple of the args to the datalist """
    datalist.append(tuple(element for element in args))
