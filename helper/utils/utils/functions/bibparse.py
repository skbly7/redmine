# -*- coding: utf-8 -*-
def bib2csv(file):
    from pybtex.database.input import bibtex
    data = []
    header = {}

    parser = bibtex.Parser()
    bibdata = parser.parse_file(file)
    for bib_id in bibdata.entries:
        b = bibdata.entries[bib_id].fields
        for key in b.keys():
            if key not in header:
                header[key] = len(header)

        # print bibdata.entries[bib_id]
        """
        FieldDict([('title', 'StreamJIT: A Commensal Compiler for High-performance Stream Programming'),
        ('journal', 'SIGPLAN Not.'), ('issue_date', 'October 2014'), ('volume', '49'),
        ('number', '10'), ('month', 'October'), ('year', '2014'), ('issn', '0362-1340'),
        ('pages', '177--195'), ('numpages', '19'), ('url', 'http://doi.acm.org/10.1145/2714064.2660236'),
        ('doi', '10.1145/2714064.2660236'), ('acmid', '2660236'), ('publisher', 'ACM'),
        ('address', 'New York, NY, USA'),
        ('keywords', 'domain-specific languages, embedded domain-specific languages')])
        """
        current = []
        for key, _value in sorted(header.iteritems(), key=lambda (k,v): v):
            value = ''
            if key in b:
                value = b[key]
            current.append(value)
        data.append(current)
    print header
    print data[2]
