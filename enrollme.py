from bs4 import BeautifulSoup
from datetime import timedelta
import json
import requests
from requests import Session
from requests.utils import cookiejar_from_dict
import translitcodec
from urlparse import urlparse, parse_qs

from objects import Subject, Teacher


class EnrollMeClient(object):
    def __init__(self, url, view_state, jsessionid):
        self._url_tpl = url + '/app/admin?execution=%s'
        self.view_state = view_state
        self.session = Session()
        self.session.cookies = cookiejar_from_dict({
            'JSESSIONID': jsessionid,
            'primefaces.download': 'true',
        })
        self.session.headers = {
            'Accept': 'application/xml, text/xml, */*; q=0.01',
            'Faces-Request': 'partial/ajax',
            'X-Requested-With': 'XMLHttpRequest',
        }

    @property
    def url(self):
        return self._url_tpl % self.view_state

    def get_subjects(self):
        data = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.partial.execute': 'form:subjectChoice',
            'javax.faces.partial.render': 'form:subjectChoice',
            'form:subjectChoice_query': '',
            'javax.faces.ViewState': self.view_state,
        }
        r = self.session.post(self.url, data=data)
        response = BeautifulSoup(r.text)
        self.view_state = response.find('update', {'id': 'javax.faces.ViewState'}).text
        update = response.find('update', {'id': 'form:subjectChoice'})
        document = BeautifulSoup(update.text)
        subjects_list = document.find('ul').find_all('li')
        for subject in subjects_list:
            yield Subject(int(subject['data-item-value']), subject.text)

    def get_teachers(self):
        data = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.partial.execute': 'form:teacherChoice',
            'javax.faces.partial.render': 'form:teacherChoice',
            'form:teacherChoice_query': '',
            'javax.faces.ViewState': self.view_state,
        }
        r = self.session.post(self.url, data=data)
        response = BeautifulSoup(r.text)
        self.view_state = response.find('update', {'id': 'javax.faces.ViewState'}).text
        update = response.find('update', {'id': 'form:teacherChoice'})
        document = BeautifulSoup(update.text)
        teachers_list = document.find('ul').find_all('li')
        for teacher in teachers_list:
            title, first_name, last_name = teacher.text.rsplit(' ', 2)
            yield Teacher(int(teacher['data-item-value']), title, first_name, last_name)

    def _set_term_date(self, date):
        data = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'form:j_id_1v',
            'javax.faces.partial.execute': 'form:j_id_1v',
            'javax.faces.partial.render': 'form:eventDetails form:messages',
            'javax.faces.behavior.event': 'dateSelect',
            'javax.faces.partial.event': 'dateSelect',
            'form:j_id_1v_selectedDate': date.strftime('%s000'),
            'form_SUBMIT': '1',
            'javax.faces.ViewState': self.view_state,
        }
        self.session.post(self.url, data=data)

    def add_term(self, term):
        date = term.date + timedelta(hours=1)
        self._set_term_date(date)
        data = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'form:j_id_35',
            'javax.faces.partial.execute': '@all',
            'javax.faces.partial.render': 'form:messages',
            'form:j_id_35': 'form:j_id_35',
            'form:subjectChoice_hinput': term.subject.id,
            'form:teacherChoice_hinput': term.teacher.id,
            'form:place': term.location,
            'form:type': term.class_type,
            'form:capacity': term.max_people,
            'form:minimalCapacity': term.min_people,
            'form:divisibility': term.team_size,
            'form:weekType_input': 'YEAR_' + (term.year if term.year else 'ALL'),
            'form:firstOccurrence_input': date.strftime('%m/%d/%Y %H:%M:%S'),
            'form:lastOccurrence_input': '06/22/2015 23:59:59',
            'form:departmentGroup': term.group,
            'form_SUBMIT': '1',
            'javax.faces.ViewState': self.view_state,
        }
        if term.is_certain:
            data['form:certain_input'] = 'on'
        self.session.post(self.url, data=data)

    def _select_term_by_uuid(self, uuid):
        data = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'form:j_id_1v',
            'javax.faces.partial.execute': 'form:j_id_1v',
            'javax.faces.partial.render': 'form:eventDetails',
            'javax.faces.behavior.event': 'eventSelect',
            'javax.faces.partial.event': 'eventSelect',
            'form:j_id_1v_selectedEventId': uuid,
            'javax.faces.ViewState': self.view_state,
        }
        self.session.post(self.url, data=data)

    def update_term(self, term):
        date = term.date + timedelta(hours=1)
        self._select_term_by_uuid(term.uuid)
        data = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'form:j_id_35',
            'javax.faces.partial.execute': '@all',
            'javax.faces.partial.render': 'form:messages',
            'form:j_id_35': 'form:j_id_35',
            'form:subjectChoice_hinput': term.subject.id,
            'form:teacherChoice_hinput': term.teacher.id,
            'form:place': term.location,
            'form:type': term.class_type,
            'form:capacity': term.max_people,
            'form:minimalCapacity': term.min_people,
            'form:divisibility': term.team_size,
            'form:weekType_input': 'YEAR_' + (term.year if term.year else 'ALL'),
            'form:firstOccurrence_input': date.strftime('%m/%d/%Y %H:%M:%S'),
            'form:lastOccurrence_input': '06/22/2015 23:59:59',
            'form:departmentGroup': term.group,
            'form_SUBMIT': '1',
            'javax.faces.ViewState': self.view_state,
        }
        if term.is_certain:
            data['form:certain_input'] = 'on'
        self.session.post(self.url, data=data)

    def _get_term_by_uuid(self, uuid, term_class):
        data = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'form:j_id_1v',
            'javax.faces.partial.execute': 'form:j_id_1v',
            'javax.faces.partial.render': 'form:eventDetails',
            'javax.faces.behavior.event': 'eventSelect',
            'javax.faces.partial.event': 'eventSelect',
            'form:j_id_1v_selectedEventId': uuid,
            'javax.faces.ViewState': self.view_state,
        }
        r = self.session.post(self.url, data=data)
        response = BeautifulSoup(r.text)
        self.view_state = response.find('update', {'id': 'javax.faces.ViewState'}).text
        update = response.find('update', {'id': 'form:eventDetails'})
        document = BeautifulSoup(update.text)
        term_data = {
            'uuid': uuid,
            'id': document.find('span', {'id': 'form:termId'}),
            'class_type': document.find('input', {'id': 'form:type'}),
            'group': document.find('input', {'id': 'form:departmentGroup'}),
            'subject_id': document.find('span', {'id': 'form:subjectId'}),
            'location': document.find('input', {'id': 'form:place'}),
            'is_certain': document.find('input', {'id': 'form:certain_input'}),
            'max_people': document.find('input', {'id': 'form:capacity'}),
            'min_people': document.find('input', {'id': 'form:minimalCapacity'}),
            'team_size': document.find('input', {'id': 'form:divisibility'}),
            'teacher_id': document.find('input', {'id': 'form:teacherChoice_hinput'}),
            'year': document.find('select', {'id': 'form:weekType_input'}).find('option', {'selected': True}),
            'start_time': document.find('span', {'id': 'form:startTime'}),
        }
        return term_class(term_data) 

    def get_terms(self, term_class):
        data = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'form:j_id_1v',
            'javax.faces.partial.execute': 'form:j_id_1v',
            'javax.faces.partial.render': 'form:j_id_1v',
            'form:j_id_1v': 'form:j_id_1v',
            'javax.faces.ViewState': self.view_state,
        }
        r = self.session.post(self.url, data=data)
        response = BeautifulSoup(r.text)
        self.view_state = response.find('update', {'id': 'javax.faces.ViewState'}).text
        update = response.find('update', {'id': 'form:j_id_1v'})
        timetable = json.loads(update.text)
        for event in timetable['events']:
            yield self._get_term_by_uuid(event['id'], term_class)

    def get_preferences(self):
        data = {
            'sub-navbar:import_export_button': '',
            'sub-navbar_SUBMIT': '1',
            'javax.faces.ViewState': self.view_state,
        }
        r = requests.post(self.url, data=data, cookies=self.session.cookies)
        url = urlparse(r.url)
        query = parse_qs(url.query)
        self.view_state = query['execution'][0]
        data = {
            'downloading:downloadPreferencesAnt': '',
            'downloading_SUBMIT': '1',
            'javax.faces.ViewState': self.view_state,
        }
        r = requests.post(self.url, data=data, cookies=self.session.cookies)
        url = urlparse(r.url)
        query = parse_qs(url.query)
        self.view_state = query['execution'][0]
        return r.text
