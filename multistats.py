#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from collections import Counter, defaultdict
from ConfigParser import SafeConfigParser
from datetime import date, datetime, timedelta
import translitcodec
from StringIO import StringIO
from time import sleep

from enrollme import EnrollMeClient
import settings
from urlparse import urlparse, parse_qs
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


class SubjectNotFound(KeyError):
    pass


class TeacherNotFound(KeyError):
    pass


class Term(object):
    def __init__(self, data):
        for k, v in data.items():
            getattr(self, '_convert_' + k)(v)

    def _convert_id(self, id):
        self.id = int(id.text)

    def _convert_uuid(self, uuid):
        self.uuid = uuid

    def _convert_class_type(self, class_type):
        self.class_type = class_type['value']

    def _convert_group(self, group):
        if group['value'] == '0':
            self.group = None
        else:
            self.group = group['value']

    def _convert_subject_id(self, id):
        try:
            self.subject = subject_by_id[int(id.text)]
        except KeyError:
            raise SubjectNotFound(id.text)

    def _convert_location(self, location):
        self.location = location['value']

    def _convert_is_certain(self, is_certain):
        self.is_certain = (is_certain.get('checked', '') != '')

    def _convert_max_people(self, max_people):
        self.max_people = int(max_people['value'])

    def _convert_min_people(self, min_people):
        self.min_people = int(min_people['value'])

    def _convert_team_size(self, team_size):
        self.team_size = int(team_size['value'])

    def _convert_teacher_id(self, id):
        try:
            self.teacher = teacher_by_id[int(id['value'])]
        except KeyError:
            raise TeacherNotFound(id['value'])

    def _convert_year(self, year):
        if year.text == 'ALL':
            self.year = None
        else:
            self.year = year.text

    def _convert_start_time(self, start_time):
        self.date = datetime.strptime(start_time.text, '%d/%m/%Y %I:%M %p')

    def __str__(self):
        return (str(self.subject) + ' - ' + self.class_type +
                (' (gr. ' + self.group + ')' if self.group else '') + ' - ' +
                self.teacher.name + ' - ' +
                self.date.strftime('%a, %H:%M') +
                (' (week ' + self.year + ')' if self.year else '') + ' - ' +
                (str(self.max_people) + ' spots' if self.max_people else '') +
                ('min. ' + str(self.min_people) + ' spots' if self.min_people else ''))

    def __lt__(self, other):
        return self.date < other.date or (self.date == other.date and self.year < other.year)

    def __gt__(self, other):
        return self.date > other.date or (self.date == other.date and self.year > other.year)


cookies = {
    'JSESSIONID': settings.JSESSIONID,
}

client = EnrollMeClient(settings.ENROLL_URL, settings.VIEW_STATE, settings.JSESSIONID)

teacher_by_id = dict([(t.id, t) for t in client.get_teachers()])

from jinja2 import Environment, PackageLoader
env = Environment(loader=PackageLoader('stats', 'templates'))
template = env.get_template('stats.html')

import paramiko
import os

hostname = settings.SSH_HOSTNAME
host_keys = paramiko.util.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))

if hostname in host_keys:
    hostkeytype = host_keys[hostname].keys()[0]
    hostkey = host_keys[hostname][hostkeytype]
    print('Using host key of type %s' % hostkeytype)

t = paramiko.Transport((hostname, 22))
t.connect(hostkey, settings.SSH_USERNAME, settings.SSH_PASSWORD)
sftp = paramiko.SFTPClient.from_transport(t)

zapisy = [
    ('Zapisy - 3 rok - 6 semestr', 'rok3-sem6', 20, 8),
    ('Zapisy - 2 rok - 4 semestr', 'rok2-sem4', 20, 8),
    ('Zapisy - 1 rok - 2 semestr', 'rok1-sem2', 20, 10),
]

for title, filename, MAX_SUBJECT_PRECIOUSNESS, MAX_TERM_PRECIOUSNESS in zapisy:    
    admin = settings.driver.find_element_by_link_text('Admin panel')
    admin.click()
    settings.wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Are you sure you want to leave view?')]")))
    yes = settings.driver.find_element_by_xpath("//*[contains(text(), 'Are you sure you want to leave view?')]/following::*[contains(text(), 'Yes')]")
    yes.click()
    settings.wait.until(lambda driver: 'Select enrollment to configure from the list bellow.' in settings.driver.page_source)
    configure = settings.driver.find_element_by_xpath("//*[contains(text(), '" + title + "')]/following::*[contains(text(), 'Configure')]")
    configure.click()
    settings.wait.until(lambda driver: 'Configure enrollment' in settings.driver.page_source)
    button = settings.driver.find_element_by_xpath("//*[contains(text(), 'Terms')]")
    button.click()
    settings.wait.until(lambda driver: 'Terms management' in settings.driver.page_source)
    url = urlparse(settings.driver.current_url)
    query = parse_qs(url.query)
    settings.VIEW_STATE = query['execution'][0]
    client.view_state = settings.VIEW_STATE

    subject_by_id = dict([(s.id, s) for s in client.get_subjects()])
    term_by_id = {}
    terms_by_subject = defaultdict(list)
    for t in client.get_terms(Term):
        term_by_id[t.id] = t
        if not t.is_certain:
            terms_by_subject[t.subject].append(t)

    TERMS_MAX_PRECIOUSNESS = Counter()

    prefs = StringIO(client.get_preferences())
    prefs_parser = SafeConfigParser(allow_no_value=True)
    prefs_parser.readfp(prefs)

    for student_id in prefs_parser.sections():
        for subject_id, prefs in prefs_parser.items(student_id):
            prefs = prefs.strip(';').split(';')
            for pref in prefs:
                term_id, preciousness = pref.split(',', 1)
                preciousness = MAX_SUBJECT_PRECIOUSNESS - int(preciousness)
                if preciousness == MAX_TERM_PRECIOUSNESS:
                    TERMS_MAX_PRECIOUSNESS[int(term_id)] += 1

    import locale
    locale.setlocale(locale.LC_TIME, 'pl_PL.utf8')

    with sftp.open('WWW/stats/' + filename + '.html', 'w') as f:
        f.write(template.render(terms_by_subject=terms_by_subject, terms_max_preciousness=TERMS_MAX_PRECIOUSNESS, now=datetime.now()))

    locale.setlocale(locale.LC_TIME, 'C')
settings.driver.quit()
