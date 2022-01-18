import time
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait


# noinspection SpellCheckingInspection
class ManageEntrypoint:
    def __init__(self, user, password, use_shifter):
        self.user = user
        self.password = password
        self.use_shifter = use_shifter
        self.options = Options()
        self.options.headless = os.environ.get('HEADLESS_BROWSER', 'True').lower() == 'true'
        self.driver = webdriver.Firefox(options=self.options)

    def shutdown(self):
        self.driver.quit()

    def slow_down(self):
        if not self.options.headless:
            time.sleep(1)

    def start(self):
        self.login()
        self.open_entrypoint_view()
        self.add_entrypoint()
        self.select_entrypoint()
        self.cancel_update_entrypoint()
        self.update_entrypoint()
        self.clear_entrypoint()
        self.delete_entrypoint()

    def login(self):
        # Open the browser
        url = os.environ.get('HUB_URL', 'http://localhost:8000')
        self.driver.get(url)
        self.driver.implicitly_wait(10)

        # Login with dummy credentials
        self.driver.find_element(By.ID, 'username_input').send_keys(self.user)
        self.driver.find_element(By.ID, 'password_input').send_keys(self.password)
        self.slow_down()
        self.driver.find_element(By.ID, 'login_submit').click()

    def open_entrypoint_view(self):
        # Open the services tab, then the entrypoint view
        services_button = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Services')]")[0]
        services_button.click()

        entrypoint_button = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'entrypoint')]")[0]
        entrypoint_button.click()

        for el in self.driver.find_elements(By.XPATH, '//input'):
            if el.get_attribute('value') == 'Authorize':
                self.slow_down()
                el.click()
                break

        elem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Favorite Entrypoint')]")
        assert 'None' in elem.text
        elems = self.driver.find_elements(By.NAME, 'selected_entrypoint')
        assert len(elems) == 1 and elems[0].is_selected() and elems[0].get_attribute('value') == ''

    def add_entrypoint(self):
        if self.use_shifter:
            elem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Shifter Entrypoints')]")
        else:
            elem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Trusted Script Entrypoints')]")

        self.try_click(elem.find_element(By.XPATH, './/a'))

        name_input = self.driver.find_element(By.NAME, 'entrypoint_name')
        name_input.send_keys('my-env')
        self.driver.find_element(By.NAME, 'image' if self.use_shifter else 'script').click()
        if self.use_shifter:
            opt = self.driver.find_element(By.XPATH,
                                           "//option[contains(text(), 'jenkins:latest')]")
        else:
            opt = self.driver.find_element(By.XPATH,
                                           "//option[contains(text(), '/usr/local/bin/example-entrypoint.sh')]")

        opt.click()
        self.slow_down()
        self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]").click()

    '''
    We use thiss loop to workaround exception "not clickable because another element obscures it"
    Interestingly we only see this exception  when testing shifter environment. 
    '''
    @staticmethod
    def try_click(elem):
        from selenium.common.exceptions import ElementClickInterceptedException
        i = 0
        while True:
            try:
                elem.click()
                break
            except ElementClickInterceptedException as e:
                i += 1

                if i == 100:
                    raise e
                time.sleep(0.2)

    def select_entrypoint(self):
        elems = self.driver.find_elements(By.NAME, 'selected_entrypoint')
        elems = list(filter(lambda e: e.get_attribute('value') == 'my-env', elems))
        self.try_click(elems[0])
        self.slow_down()
        elem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Favorite Entrypoint')]")
        assert 'my-env' in elem.text

    def cancel_update_entrypoint(self):
        button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'delete')]")
        button = button.find_element(By.XPATH, './..').find_element(By.XPATH, './/a')
        self.try_click(button)
        button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
        button = button.find_element(By.XPATH, './..').find_element(By.XPATH, './/a')
        self.slow_down()
        button.click()
        elem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Favorite Entrypoint')]")
        assert 'my-env' in elem.text

    def update_entrypoint(self):
        button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'delete')]")
        button = button.find_element(By.XPATH, './..').find_element(By.XPATH, './/a')
        self.try_click(button)
        name_input = self.driver.find_element(By.NAME, 'entrypoint_name')
        name_input.send_keys('updated-env')
        button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
        self.slow_down()
        button.click()
        elem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Favorite Entrypoint')]")
        assert 'updated-env' in elem.text

    def clear_entrypoint(self):
        elems = self.driver.find_elements(By.NAME, 'selected_entrypoint')
        list(filter(lambda e: e.get_attribute('value') == '', elems))[0].click()
        self.slow_down()
        elem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Favorite Entrypoint')]")
        assert 'None' in elem.text

    def delete_entrypoint(self):
        button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'delete')]")
        self.try_click(button)
        WebDriverWait(self.driver, 10).until(ec.alert_is_present())
        self.driver.switch_to.alert.accept()
        time.sleep(1)
        elems = self.driver.find_elements(By.NAME, 'selected_entrypoint')
        assert len(elems) == 1 and elems[0].is_selected()


def test1():
    t = ManageEntrypoint('admin', 'admin', False)
    t.start()
    t.shutdown()


def test2():
    t = ManageEntrypoint('user1', 'user1', True)
    t.start()
    t.shutdown()
