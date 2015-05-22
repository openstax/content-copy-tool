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

    def setup(self):
        # self.driver = webdriver.Firefox()
        # chrome driver option
        self.driver = webdriver.Chrome('/Users/westonnovelli/Documents/textbook-migration/research/selenium-tests/util/chromedriver')
        self.config = util.parse_input('config.json')
        self.logger = util.init_logger(self.config['create_module_log_file'])

    def teardown(self):
        util.tearDown(self.driver)

    def create_module(self):
        # navigate to site
        server_url = self.config['create_module_on_server']
        if not re.match('https?://', server_url):
            self.logger.debug("Prepending \'http://\' to server url.")
            server_url='http://' + server_url
        self.driver.get(server_url)
        self.driver.implicitly_wait(300)

        # login
        self.logger.info("Logging in.")
        util.login(self.driver, str(self.config['create_module_with_credentials']))
        self.driver.implicitly_wait(300)

        # self.driver.get('https://legacydev.cnx.org/GroupWorkspaces/wg2935')
        # begin create module
        self.logger.info("Creating module.")
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
        name.send_keys(str(self.config['create_module_with_title'])+str(datetime.datetime.now()))
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
        self.logger.info("Extracting module ID.")
        moduleID_field = self.driver.find_element_by_css_selector('#region-content > div > div > table > tbody > tr:nth-child(2) > td')
        moduleID = moduleID_field.get_attribute('innerHTML')
        self.logger.info("Created module with ID: " + moduleID)
        print(moduleID)

    def run_create_module(self):
        self.setup()
        self.create_module()
        self.teardown()

if __name__ == "__main__":
    mc = ModuleCreator()
    mc.run_create_module()
