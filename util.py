import json
import logging
import datetime

def init_logger(filename):
    """
    Initializes and returns a basic logger to the specified filename.
    """
    logger = logging.getLogger('content-copy')
    logger.setLevel(logging.INFO)
    if 'console' in filename:
        if 'Verbose' in filename:
            logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
    else:
        handler = logging.FileHandler(filename)
    formatter = logging.Formatter('"%(asctime)s - %(name)s - %(levelname)s - %(message)s"')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
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
    return json.dumps(data, indent=4)

def tearDown(driver):
    driver.quit()

def quick_succession_reset(driver, reset_page):
    mycnx_link = driver.find_element_by_link_text('MyCNX')
    mycnx_link.click()

def write_list_to_file(datalist, booktitle):
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
    datalist.append(tuple(element for element in args))
