# ----------------------------------------------------------------------------------- #
# [Description]: Common methods                                                       #
# ----------------------------------------------------------------------------------- #

from urllib.parse import unquote, unquote_plus, urlparse, parse_qs, urlencode, urlunparse
from config import scraperEngine, paramsOfInterest, param2Remove
from datetime import datetime


def recoverSedoKw(url):
    ''' Extracts kw from sedo url in fb_kws_other's row format'''
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    row = {
        'kw1'   : query.get('kw1',[0])[0],
        'kw2'   : query.get('kw2',[0])[0],
        'kw3'   : query.get('kw3',[0])[0],
        'kw4'   : query.get('kw4',[0])[0],
        'kw5'   : query.get('kw5',[0])[0],
        'kw6'   : query.get('kw6',[0])[0],
        'kw7'   : query.get('kw7',[0])[0],
        'kw8'   : query.get('kw8',[0])[0],
        'feed'  : 'sedo',
    }
    return row if row else []


def recoverIACkw(url):
    ''' Extracts kw from IAC scheme in fb_kws_other's row format'''
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    row = {
        'kw1'   : query.get('KW1',[0])[0],
        'kw2'   : query.get('KW2',[0])[0],
        'kw3'   : query.get('KW3',[0])[0],
        'kw4'   : query.get('KW4',[0])[0],
        'kw5'   : query.get('KW5',[0])[0],
        'kw6'   : query.get('KW6',[0])[0],
        'kw7'   : query.get('KW7',[0])[0],
        'kw8'   : query.get('KW8',[0])[0],
        'feed'  : 'iac',
    }
    return row if row else []


def recoverDAkw(url):
    ''' Extracts kw from IAC scheme in fb_kws_other's row format'''
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    row = {
        'kw1'   : query.get('aff_usb',[0])[0],
        'kw2'   : query.get('aff_sub2',[0])[0],
        'kw3'   : query.get('aff_sub3',[0])[0],
        'kw4'   : '',
        'kw5'   : '',
        'kw6'   : '',
        'kw7'   : '',
        'kw8'   : '',
        'feed'  : 'da',
    }
    return row if row else []


def recoverOthers(url):
    ''' Extracts kw from IAC scheme in fb_kws_other's row format'''
    counter = 0
    row={}
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    keyList = list(query.keys())
    for key in paramsOfInterest['others']:
        if key in keyList:
            row['kw'+str(counter+1)] = query[key][0]
            counter +=1
    if row:
        while counter < 8:
            row['kw'+str(counter+1)] = 0  # Fulfill all columns with zero
            counter +=1
        row['feed'] = 'others'
        return row
    else:
        return []


recoverKw = {
    'sedo': recoverSedoKw,
    'iac':  recoverIACkw,
    'da':   recoverDAkw,
    'others':  recoverOthers,
}


def removeArgs(link):
    ''' Substracts fbclid and h parameter from link '''
    parsed = urlparse(link)
    query = parse_qs(parsed.query)
    for param in param2Remove:
        query.pop(param,'')
    parsed = parsed._replace(query=urlencode(query,True))
    return urlunparse(parsed)


def checkUrl4Kw(url):
    ''' Categorizes url and extract keywords if scheme recognized'''
    feed = ''
    decodedUrl = unquote_plus(url)
    decodedUrl = removeArgs(decodedUrl)
    parsed = urlparse(decodedUrl)
    query = parse_qs(parsed.query)
    ks = list(query.keys())
    row = False

    if any(item in ks for item in paramsOfInterest['sedo']):
        feed = 'sedo'
    elif any(item in ks for item in paramsOfInterest['iac']):
        feed = 'iac'
    elif any(item in ks for item in paramsOfInterest['da']):
        feed = 'da'
    elif any(item in ks for item in paramsOfInterest['others']):
        feed = 'others'
    else:
        pass
    
    if feed:
        res = recoverKw[feed](decodedUrl)
        if res:
            row = res
    return row