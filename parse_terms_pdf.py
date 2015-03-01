# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTFigure, LTLine

from collections import defaultdict
import errno
import os

mapa = (
    ('\x15', '-'),
    ('\xc2\xab', 'ń'),
    ('\xc2\xaa', 'ł'),
    ('\xc2\x9b', 'Ż'),
    ('\xc2\xa6', 'ę'),
    ('\xc2\xbb', 'ż'),
    ('\xc2\x8a', 'Ł'),
    ('\xc2\xb1', 'ś'),
    ('\xc2\x82', 'Ć'),
    ('\xc2\xb9', 'ź'),
    ('\xc2\xa1', 'ą'),
    ('\xc2\x91', 'Ś'),
    ('\x1c', 'fi'),
)


class rangelist(list):
    def append(self, value):
        for index, item in enumerate(self):
            if value[1] == item[0]:
                self[index] = value[0], item[1]
                return
            elif item[1] == value[0]:
                self[index] = item[0], value[1]
                return
        super(rangelist, self).append(value)

    def __contains__(self, item):
        for beg, end in self:
            if item > beg and item < end:
                return True
        return False


def sanitize(text):
    for old, new in mapa:
        text = text.replace(old, new)
    return text


def parse_layout(layout):
    """Function to recursively parse the layout tree."""
    for lt_obj in layout:
        x1, y1, x2, y2 = lt_obj.bbox
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        if isinstance(lt_obj, LTTextLine):
            document[y1].append((x1, sanitize(lt_obj.get_text().strip())))
        elif isinstance(lt_obj, LTLine):
            x1, y1, x2, y2 = lt_obj.bbox
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            if x1 == x2:
                borders[x1].append((y1, y2))
        elif isinstance(lt_obj, LTFigure) or isinstance(lt_obj, LTTextBox):
            parse_layout(lt_obj)  # Recursive


fp = open(sys.argv[1], 'rb')
parser = PDFParser(fp)
doc = PDFDocument(parser)

subjects = []

rsrcmgr = PDFResourceManager()
laparams = LAParams()
laparams.char_margin = 1.5
device = PDFPageAggregator(rsrcmgr, laparams=laparams)
interpreter = PDFPageInterpreter(rsrcmgr, device)
subject = []
key = None
enr = None
for page in PDFPage.create_pages(doc):
    document = defaultdict(list)
    borders = defaultdict(rangelist)
    interpreter.process_page(page)
    layout = device.get_result()
    parse_layout(layout)
    items = sorted(document.items(), reverse=True)
    for y, texts in items[:-1]:
        d = dict()
        for x, text in sorted(texts):
            col = 0
            for x_border, y_range in sorted(borders.items()):
                if x < x_border:
                    break
                if y in y_range:
                    col += 1
            d[col] = text
        i = d.get(0)
        if not i:
            subject.append('\t'.join([d.get(i, '') for i in xrange(1, 7)]))
        else:
            if key:
                if subject:
                    with open(os.path.join('terms', enr, key + '.txt'), 'w') as f:
                        f.write('\n'.join(subject))
                else:
                    enr = key
                    try:
                        os.mkdir(os.path.join('terms', key))
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            raise e
            key = i
            subject = []
if key and subject:
    with open(os.path.join('terms', enr, key + '.txt'), 'w') as f:
        f.write('\n'.join(subject))
