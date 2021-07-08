import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.firefox.options import Options

class Test():
    def setup_method(self, method):
        options = Options()
        options.headless = True
        self.driver = webdriver.Firefox(options=options)
        self.vars = {}
    
    def teardown_method(self, method):
        self.driver.quit()

    def wait_for_window(self, timeout = 2):
        time.sleep(round(timeout / 1000))
        wh_now = self.driver.window_handles
        wh_then = self.vars["window_handles"]
        if len(wh_now) > len(wh_then):
            return set(wh_now).difference(set(wh_then)).pop()
    
    def test(self):
        self.driver.get('http://localhost:8000')
        self.driver.implicitly_wait(10)

        username = self.driver.find_element_by_id('username_input')
        password = self.driver.find_element_by_id('password_input')

        username.send_keys('admin')
        password.send_keys('admin')

        login_button = self.driver.find_element_by_id('login_submit')
        login_button.click()

        services_button = self.driver.find_elements_by_xpath("//*[contains(text(), 'Services')]")[0]
        services_button.click()

        entrypoint_button = self.driver.find_elements_by_xpath("//*[contains(text(), 'entrypoint')]")[0]
        entrypoint_button.click()

        title = self.driver.find_element_by_id('title')

        assert title.text == 'JupyterHub Entrypoint Service'
