class Subject(object):
    def __init__(self, id, name):
        self.name = name
        self.id = id

    def __str__(self):
        return self.name

    def __lt__(self, other):
        return self.name < other.name

    def __gt__(self, other):
        return self.name > other.name


class Teacher(object):
    def __init__(self, id, title, first_name, last_name):
        self.id = id
        self.title = title
        self.first_name = first_name
        self.last_name = last_name

    @property
    def name(self):
        return self.last_name + ' ' + self.first_name

    @property
    def short_name(self):
        return self.first_name[0] + '. ' + self.last_name

    def __str__(self):
        return self.name

    def __lt__(self, other):
        return self.name < other.name

    def __gt__(self, other):
        return self.name > other.name
