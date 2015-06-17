# This is a Selenium script that creates a workgroup.

import re

from selenium import webdriver

import util as util

##################
# NOT IN USE
##################
class WorkgroupCreator():
    '''
    This creates a workgroup on the specified server with the specified information
    '''

    def __init__(self, logger):
        self.logger = logger

    def setup(self):
        # self.driver = webdriver.Firefox()
        # chrome driver option
        self.driver = webdriver.Chrome('/Users/westonnovelli/Documents/textbook-migration/research/selenium-tests/util/chromedriver')

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
        self.logger.debug("Logging in.")
        util.login(self.driver, credentials)
        # self.driver.implicitly_wait(300)

        # self.driver.get('https://legacydev.cnx.org/GroupWorkspaces/wg2935')
        # create workgroup
        self.logger.debug("Creating workgroup.")
        create_link = self.driver.find_element_by_link_text('Create a Workgroup')
        create_link.click()
        name = self.driver.find_element_by_name('title')
        name.clear()
        name.send_keys(title)
        create_btn = self.driver.find_element_by_name('form.button.Register')
        create_btn.click()

        # get ID
        self.logger.debug("Extracting workgroup ID.")
        url = self.driver.current_url
        workgroupID = re.search('GroupWorkspaces/wg[0-9]+', url)
        if workgroupID:
            workgroupID = re.search('wg[0-9]+', workgroupID.group(0)).group(0)
        if workgroupID == None:
            self.logger.error("Workgroup ID is None")
        else:
            self.logger.debug("Created Workgroup with ID: " + workgroupID)
            return workgroupID
        return ''

    def run_create_workgroup(self, title, server, credentials, dryrun=False):
        """
        Runs selenium to create a workgroup with the given information

        Arguments:
          title       - the title of the workgroup
          server      - the server to create the workgroup on
          credentials - the username:password to use when creating the workgroup
          dryrun      - (optional) a flag to step through the setup and teardown
                        without actually creating the workgroup

        Returns:
          the ID of the created workgroup, 'wg0000' if dryrun or failure
        """
        self.setup()
        info_str = "Creating workgroup: "+title+" on "+server
        self.logger.info(info_str)
        res = 'wg00000'
        if not dryrun:
            res = self.create_workgroup(title, server, credentials)
        self.teardown()
        return res

# if __name__ == "__main__":
#     wgc = WorkgroupCreator()
#     wgc.run_create_workgroup()
