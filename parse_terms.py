#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import csv
from datetime import date, datetime, timedelta
import translitcodec

from enrollme import EnrollMeClient
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

    def __str__(self):
        return (str(self.subject) + ' - ' + self.class_type +
                (' (gr. ' + self.group + ')' if self.group else '') + ' - ' +
                self.teacher.name + ' - ' +
                self.date.strftime('%a, %H:%M') +
                (' (week ' + self.year + ')' if self.year else '') + ' - ' +
                (str(self.max_people) + ' spots' if self.max_people else '') +
                ('min. ' + str(self.min_people) + ' spots' if self.min_people else ''))


cookies = {
    'JSESSIONID': settings.JSESSIONID,
}

client = EnrollMeClient(settings.URL, settings.VIEW_STATE, settings.JSESSIONID)
subject_by_name = dict([(s.name.encode('translit/short'), s) for s in client.get_subjects()])
teacher_by_name = dict([(t.name.encode('translit/short'), t) for t in client.get_teachers()])

subjects_not_found = set()
teachers_not_found = set()

terms_list = []
barrier = False

with open('terms.txt', "rb") as ifile:
    reader = csv.DictReader(ifile, delimiter='\t')
    for row in reader:
        try:
            t = Term(row)
        except SubjectNotFound as e:
            subjects_not_found.add(e.message)
            barrier = True
        except TeacherNotFound as e:
            teachers_not_found.add(e.message)
            barrier = True
        else:
            terms_list.append(t)

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

settings.driver.execute_script("alert('Import started! You can monitor progress in terminal window...');")
for term in terms_list:
    print 'Adding term ' + str(term) + '...'
    client.add_term(term)

settings.driver.refresh()
settings.driver.execute_script("alert('Import finished - check if everything was added correctly and save changes.');")
