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

import csv
import settings

WEEKDAYS = dict(Pn=0, Wt=1, Sr=2, Cz=3, Pt=4, Sb=5, Nd=6)

TODAY = date.today()
WEEK_START = TODAY - timedelta(days=TODAY.weekday())


class SubjectNotFound(KeyError):
    pass


class TeacherNotFound(KeyError):
    pass


class Term(object):
    def __init__(self, data):
        for k, v in data.items():
            getattr(self, '_convert_' + k)(v)

    def _convert_uuid(self, uuid):
        self.uuid = uuid

    def _convert_id(self, id):
        self.id = int(id.text)

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


class Term2(Term):
    def __init__(self, data):
        for k, v in data.items():
            getattr(self, '_convert_' + k)(v)

    def _convert_id(self, id):
        self.id = int(id)

    def _convert_class_type(self, class_type):
        if class_type.startswith('W'):
            self.class_type = u'wykład'
        elif class_type.startswith('C'):
            self.class_type = u'ćwiczenia'
        elif class_type.startswith('L'):
            self.class_type = u'laboratorium'
        else:
            self.class_type = None

    def _convert_group(self, group):
        self.group = group if group else None

    def _convert_date(self, date):
        if date.endswith((' A', ' B')):
            self.year = date[-1:]
            date = date[:-2]
        else:
            self.year = None
        weekday, hours = date.split(' ', 1)
        start_hour, end_hour = hours.split('-')
        day = WEEK_START + timedelta(days=WEEKDAYS[weekday])
        hour = datetime.strptime(start_hour, '%H:%M').time()
        when = datetime.combine(day, hour)
        self.date = when

    def _convert_subject(self, name):
        try:
            self.subject = subject_by_name[name.encode('translit/short')]
        except KeyError:
            raise SubjectNotFound(name)

    def _convert_location(self, location):
        self.location = location

    def _convert_is_certain(self, is_certain):
        self.is_certain = (is_certain != '')

    def _convert_max_people(self, max_people):
        self.max_people = int(max_people) if max_people else None

    def _convert_min_people(self, min_people):
        self.min_people = int(min_people) if min_people else None

    def _convert_team_size(self, team_size):
        self.team_size = int(team_size) if team_size else None

    def _convert_teacher(self, name):
        try:
            self.teacher = teacher_by_name[name.encode('translit/short')]
        except KeyError:
            raise TeacherNotFound(name)

client = EnrollMeClient(settings.ENROLL_URL, settings.VIEW_STATE, settings.JSESSIONID)
subject_by_id = dict([(s.id, s) for s in client.get_subjects()])
teacher_by_id = dict([(t.id, t) for t in client.get_teachers()])

subject_by_name = dict([(s.name.encode('translit/short'), s) for s in client.get_subjects()])
teacher_by_name = dict([(t.name.encode('translit/short'), t) for t in client.get_teachers()])

subjects_not_found = set()
teachers_not_found = set()

terms = {}
barrier = False

with open('terms2.txt', "rb") as ifile:
    reader = csv.DictReader(ifile, delimiter='\t')
    for row in reader:
        try:
            t = Term2(row)
        except SubjectNotFound as e:
            subjects_not_found.add(e.message)
            barrier = True
        except TeacherNotFound as e:
            teachers_not_found.add(e.message)
            barrier = True
        else:
            terms[int(t.id)] = t

if barrier:
    settings.driver.execute_script("alert('Enrollment is not ready for terms import. Correct errors shown in terminal"
                                   " and try again.');")
    print '---------'
    if subjects_not_found:
        print 'SUBJECTS NOT FOUND IN THIS ENROLLMENT:'
        print '-' + '\n- '.join(subjects_not_found)
        print '---------'
    if teachers_not_found:
        print 'TEACHERS NOT FOUND IN ENROLL-ME:'
        print '-' + '\n- '.join(teachers_not_found)
        print '---------'
    sys.exit(1)

term_by_id = {}
terms_by_subject = defaultdict(list)
for t in client.get_terms(Term):
    x = terms.get(int(t.id))
    if x:
        x.uuid = t.uuid
        print 'Updating', x
        client.update_term(x)
