# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from urlparse import urlparse, parse_qs

URL = ''

driver = webdriver.Chrome()
driver.maximize_window()
driver.get(URL)
username = driver.find_element_by_id('j_username')
username.send_keys('')
password = driver.find_element_by_id('j_password')
password.send_keys('')
submit = driver.find_element_by_id('submit')
submit.click()
wait = WebDriverWait(driver, 30)
wait.until(lambda driver: 'Welcome to Enroll-me' in driver.page_source)
admin = driver.find_element_by_link_text('Admin panel')
admin.click()
wait.until(lambda driver: 'Configure enrollment' in driver.page_source)
button = driver.find_element_by_xpath("//*[contains(text(), 'Terms')]")
button.click()
wait.until(lambda driver: 'Terms management' in driver.page_source)
url = urlparse(driver.current_url)
query = parse_qs(url.query)

JSESSIONID = driver.get_cookie('JSESSIONID')['value']
VIEW_STATE = query['execution'][0]

# Maksymalna ilość punktów do przydzielenia na przedmiot
MAX_SUBJECT_PRECIOUSNESS = 20

# Maksymalna ilość punktów do przydzielenia na termin
MAX_TERM_PRECIOUSNESS = 8
