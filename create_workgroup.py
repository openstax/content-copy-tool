# This is a Selenium script that creates a workgroup.

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
import datetime
import json
import re
import util as util

class WorkgroupCreator():
    '''
    This creates a workgroup on the specified server with the specified information
    '''

    def setup(self, logfile):
        # self.driver = webdriver.Firefox()
        # chrome driver option
        self.driver = webdriver.Chrome('/Users/westonnovelli/Documents/textbook-migration/research/selenium-tests/util/chromedriver')
        self.logger = util.init_logger(logfile)

    def teardown(self):
        util.tearDown(self.driver)

    def create_workgroup(self, title, server, credentials):
        # navigate to site
        if not re.match('https?://', server):
            self.logger.debug("Prepending \'http://\' to server url.")
            server='http://' + server
        self.driver.get(server)
        # self.driver.implicitly_wait(300)

        # login
        self.logger.info("Logging in.")
        util.login(self.driver, credentials)
        # self.driver.implicitly_wait(300)

        # self.driver.get('https://legacydev.cnx.org/GroupWorkspaces/wg2935')
        # create workgroup
        self.logger.info("Creating workgroup.")
        create_link = self.driver.find_element_by_link_text('Create a Workgroup')
        create_link.click()
        name = self.driver.find_element_by_name('title')
        name.clear()
        name.send_keys(title+str(datetime.datetime.now()))
        create_btn = self.driver.find_element_by_name('form.button.Register')
        create_btn.click()

        # get ID
        self.logger.info("Extracting workgroup ID.")
        url = self.driver.current_url
        workgroupID = re.search('GroupWorkspaces/wg[0-9]+', url)
        if workgroupID:
            workgroupID = re.search('wg[0-9]+', workgroupID.group(0)).group(0)
        if workgroupID == None:
            self.logger.error("Workgroup ID is None")
        else:
            self.logger.info("Created Workgroup with ID: " + workgroupID)
            return workgroupID
        return ''

    def run_create_workgroup(self, title, server, credentials, logfile):
        self.setup(logfile)
        res = self.create_workgroup(title, server, credentials)
        self.teardown()
        return res

# if __name__ == "__main__":
#     wgc = WorkgroupCreator()
#     wgc.run_create_workgroup()
