# This is a Selenium script that creates a module.

import unittest
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
import datetime
import json
import re
import util as util

class ModuleCreator():
    '''
    This creates a module on the specified server with the specified information
    '''

    def __init__(self, logger):
        self.logger = logger

    def setup(self):
        # self.driver = webdriver.Firefox()
        # chrome driver option
        self.driver = webdriver.Chrome('/Users/westonnovelli/Documents/textbook-migration/research/selenium-tests/util/chromedriver')

    def teardown(self):
        util.tearDown(self.driver)

    def create_and_publish_module(self, title, server, credentials, workgroup_url=''):
        # navigate to site
        if not re.match('https?://', server):
            self.logger.debug("Prepending \'http://\' to server url.")
            server ='http://' + server
        self.driver.get(server)
        # self.driver.implicitly_wait(300)

        # login
        self.logger.debug("Logging in.")
        util.login(self.driver, credentials)
        # self.driver.implicitly_wait(300)

        if workgroup_url is not '':
            self.logger.debug("Creating module in workgroup: " + workgroup_url)
            self.driver.get(workgroup_url)
            create_new_item = self.driver.find_element_by_name('workspace_factories:method')
            create_new_item.click()
            add_module_btn = self.driver.find_element_by_css_selector('#module')
            add_module_btn.click()
        else:
            self.logger.debug("Creating module.")
            create_link = self.driver.find_element_by_link_text('Create a new module')
            create_link.click()

        # agree to license agreement
        agreement_box = self.driver.find_element_by_css_selector('#region-content > div > form > div > input')
        if not agreement_box.is_selected():
            agreement_box.click()
        next_btn = self.driver.find_element_by_name('form.button.next')
        next_btn.click()

        # title module
        name = self.driver.find_element_by_name('title')
        name.clear()
        name.send_keys(title+str(datetime.datetime.now()))
        next_btn2 = self.driver.find_element_by_name('form.button.next')
        next_btn2.click()

        # publish
        publish_link = self.driver.find_element_by_css_selector('#contentview-publish > a')
        publish_link.click()
        publish_btn = self.driver.find_element_by_name('form.button.publish')
        publish_btn.click()
        # confirm publish
        publish_confirm_btn = self.driver.find_element_by_name('publish')
        publish_confirm_btn.click()

        # get ID
        self.logger.debug("Extracting module ID.")
        moduleID_field = self.driver.find_element_by_css_selector('#region-content > div > div > table > tbody > tr:nth-child(2) > td')
        moduleID = moduleID_field.get_attribute('innerHTML')
        self.logger.debug("Created module with ID: " + moduleID)
        print(moduleID)

    def run_create_and_publish_module(self, title, server, credentials, workgroup_url='', dryrun=False):
        self.setup()
        info_str = "Creating module: "+title+" on "+server
        if workgroup_url is not '':
            info_str += " in workgroup: "+str(workgroup_url)
        self.logger.info(info_str)
        if not dryrun:
            self.create_and_publish_module(title, server, credentials, workgroup_url)
        self.teardown()

# if __name__ == "__main__":
#     mc = ModuleCreator()
#     mc.run_create_and_publish_module()
