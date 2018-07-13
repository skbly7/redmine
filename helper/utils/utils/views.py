# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from .functions import bibparse
# Create your views here.
def index(request):
    success = False
    if request.method == 'POST':
        publications = download_request(request)
        buffer = pub_to_csv(publications)
        response = HttpResponse(buffer, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=publications.csv'
        return response

    return render(request, 'dlsearch.html', {
        'success': success,
        'stages': {
            'done': ['Define RQs', 'Define Protocol'],
            'ongoing': ['Conduct Search'],
            'future': ['Screen Papers', 'Data Extraction'],
        }
    })

def screen(request):
    success = False
    return render(request, 'screen.html', {
        'success': success,
        'stages': {
            'done': ['Define RQs', 'Define Protocol', 'Conduct Search'],
            'ongoing': ['Screen Papers'],
            'future': ['Data Extraction'],
            'child': ['Duplicate Finder', 'Inclusion Criteria', 'Exclusion Criteria', 'Quality Score']
        }
    })


def crawler_browser():
    import mechanize
    import cookielib
    # Browser
    br = mechanize.Browser()
    # Cookie Jar
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)
    # Browser options
    br.set_handle_equiv(True)
    br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)
    # Follows refresh 0 but not hangs on refresh > 0
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
    # Want debugging messages?
    br.set_debug_http(True)
    # User-Agent
    br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
    return br

def ieee_get_csv(keyword):
    import urllib
    import mechanize
    # Keyword processing for ieee
    keyword = keyword.replace('"', '.QT.')
    # Crawl intelligent browser
    br = crawler_browser()
    # Fake request to mimic normal user
    # TODO: Play with their analytics requests too for even more real request.
    URL = 'http://ieeexplore.ieee.org/search/searchresult.jsp?queryText='+ urllib.quote_plus(keyword) +'&newsearch=true'
    fake = br.open(URL)
    # Search request as browser
    br.set_header('Referer', URL)
    data = '{"queryText":"' + keyword + '","newsearch":"true"}'
    search = br.open(mechanize.Request('http://ieeexplore.ieee.org/rest/search', data=data, headers={"Content-type":"application/json"}))
    # Export as csv request
    params = {'bulkSetSize': 2000}
    data = urllib.urlencode(params)
    csv_request = br.open(mechanize.Request('http://ieeexplore.ieee.org/search/searchExport.jsp', data=data))
    csv_data = csv_request.read()
    return csv_data

def acm_get_csv(keyword):
    import urllib
    import mechanize
    # Crawl intelligent browser
    br = crawler_browser()
    _keyword = urllib.quote_plus(keyword)
    # Fake click via referral
    # Export as csv request
    URL = 'https://dl.acm.org/results.cfm?query=' + _keyword + '&Go.x=0&Go.y=0'
    br.set_header('Referer', URL)
    csv_request = br.open('https://dl.acm.org/exportformats_search.cfm?query=' + _keyword + '&filtered=&within=owners%2Eowner%3DHOSTED&dte=&bfr=&srt=%5Fscore&expformat=csv')
    csv_data = csv_request.read()
    return csv_data

class Publication:
    "Generic model of a publication"
    def __init__(self, title=None, year=None, authors=[], doi=None, keywords=[], abstract=None, source='Manual'):
        self.title = title
        self.year = year
        self.authors = authors
        self.doi = doi
        self.keywords = keywords
        self.abstract = abstract
        self.source = source

    def __str__(self):
        return '"' + self.title + '" by ' + ','.join(self.authors)

    def row(self):
        return [
            self.title, self.year, ', '.join(self.authors), self.doi, ', '.join(self.keywords),
            self.abstract, self.source
        ]

class PublicationCSV:
    def __init__(self, csv):
        self.mapping = None
        self.csv = None
        self.source = 'Manual'

    def get_publications(self):
        import csv
        publications = []
        csv_lines = csv.reader(self.csv[1:])
        for line in csv_lines:
            try:
                publication = Publication(title=line[self.mapping['title']],
                                          year=line[self.mapping['year']],
                                          authors=line[self.mapping['authors']].split(self.author_delim),
                                          doi=line[self.mapping['doi']],
                                          keywords=line[self.mapping['keywords']].split(self.keyword_delim),
                                          abstract=line[self.mapping['abstract']],
                                          source=self.source)
                publications.append(publication)
            except:
                pass
        return publications

class IEEEPublicationCSV(PublicationCSV):
    def __init__(self, csv):
        self.mapping = {
            'title': 0,
            'authors': 1,
            'year': 5,
            'abstract': 10,
            'doi': 13,
            'keywords': 16,
        }
        self.source = 'IEEE'
        from unidecode import unidecode
        csv = unidecode(unicode(csv, encoding = "utf-8"))
        self.csv = csv.split('\n')
        self.author_delim = ';'
        self.keyword_delim = ';'

class ACMPublicationCSV(PublicationCSV):
    def __init__(self, csv):
        self.mapping = {
            'title': 6,
            'authors': 2,
            'year': 18,
            'abstract': 24,
            'doi': 11,
            'keywords': 10,
        }
        self.source = 'ACM'
        self.csv = csv.split('\r\n')
        self.author_delim = ' and '
        self.keyword_delim = ','

def ieee_publications(keyword):
    output = ieee_get_csv(keyword)
    generator = IEEEPublicationCSV(output)
    publications = generator.get_publications()
    return publications

def acm_publications(keyword):
    output = acm_get_csv(keyword)
    generator = ACMPublicationCSV(output)
    publications = generator.get_publications()
    return publications

def pub_to_csv(publications):
    import csv
    import io
    buffer = io.BytesIO()
    wr = csv.writer(buffer, quoting=csv.QUOTE_ALL)
    for publication in publications:
        wr.writerow(publication.row())
    buffer.seek(0)
    return buffer

def download_request(request):
    keyword = request.POST.get("keyword", "")
    if keyword == "":
        raise Exception('Empty keyword not allowed.')
    publications = []
    publications += acm_publications(keyword)
    publications += ieee_publications(keyword)
    return publications

def bib2csv(request):
    if request.method == 'POST':
        csv = bibparse.bib2csv(request.FILES['file'])
        return HttpResponse(csv)
    return render(request, 'bib2csv.html')
