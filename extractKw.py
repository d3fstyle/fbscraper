# ------------------------------------------------------- #
# [Description]: Gets urls we can use to extract keywords #
# [Inputs]: table fb_sedolinks                            #
# [Outputs]: tables fb_kws                                #
# ------------------------------------------------------- #

from urllib.parse import urlparse, unquote_plus, urlunparse, parse_qs, urlencode
from config import scraperEngine, paramsOfInterest
from collections import Counter
from datetime import datetime
import pandas as pd
import re

#GETKWQUERY = '''select landing_page from fb_sedolinks where last_seen = '2023-04-11'; '''
GETKWQUERY = '''select landing_page from fb_ads where last_seen = '2023-04-16'; '''
DROPTABLE = '''drop table fb_kws'''

patterns2remove = (
    'kw1=','kw2=','kw3=','kw4=','kw5=','kw6=','kw7=','kw8=',
    'atxt=',
    'q=',
    '{city} ', 
    '{{state}}: ',
    'rskey=',
    's=',
    'ref_keyword=',
    'p=',
    'forcekeyA=','forcekeyB=','forcekeyC=','forcekeyD=','forcekeyE=','forcekeyF=',
    'compkey=')
pattern = '|'.join(map(re.escape, patterns2remove))
kws = []
urls = []
urls_filtered = []
uniqueUrls = []
unknownUrls = []

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
        'date'  : datetime.strftime(datetime.now(), "%Y-%m-%d")
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
        'date'  : datetime.strftime(datetime.now(), "%Y-%m-%d")
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
        row['date'] = datetime.strftime(datetime.now(), "%Y-%m-%d")
        return row
    else:
        return []

recoverKw = {
    'sedo': recoverSedoKw,
    'iac':  recoverIACkw,
    'others':  recoverOthers
}

def sanitizeKw(kw):
    ''' Removes unwanted characters from keyword.'''
    if kw != 0:
        kw = kw.replace('[','').replace("'",'').replace(']','')
        return kw
    else:
        return kw

response = scraperEngine.execute(GETKWQUERY)
if response:
    for row in response.all():
        urls.append(row[0])
    
    print('[INFO] - %s links to parse. %s unique links.' % (len(urls),len(uniqueUrls)))

    # Remove from links fbclid and h hash in order to compare if it's the same landing page
    for url in urls:
        decodedUrl = unquote_plus(url)
        u = urlparse(decodedUrl)
        query = parse_qs(u.query)
        query.pop('fbclid', None)
        query.pop('h', None)
        u = u._replace(query=urlencode(query,True))
        urls_filtered.append(urlunparse(u))
    print('[DEBUG] - Filtered: %s' %len(urls_filtered))
    uniqueUrls = list(dict.fromkeys(urls_filtered))
    print('[DEBUG] - Unique: %s' %len(uniqueUrls))
    urlCounter = Counter(urls_filtered)
    for url in uniqueUrls:
        decodedUrl = unquote_plus(url)
        urlquery = urlparse(decodedUrl).query
        queryDict = parse_qs(urlquery)
        ks = list(query.keys())
        for key in ks:
            if key.startswith(paramsOfInterest['sedo']):
                feed = 'sedo'
                res = recoverKw[feed](decodedUrl)
                if res:
                    kws.append(res)
                break
            elif key.startswith(paramsOfInterest['iac']):
                feed = 'iac'
                res = recoverKw[feed](decodedUrl)
                if res:
                    unknownUrls.append(res)
                break
            elif key.startswith(paramsOfInterest['others']):
                feed = 'others'
                res = recoverKw[feed](decodedUrl)
                if res:
                    unknownUrls.append(res)
                break
            else:
                continue
    
    print('[DEBUG] - Unknown kws: %s' %len(unknownUrls))
    if unknownUrls:
        print("[INFO] - Uploading %s unknown url's keywords." %len(unknownUrls))
        uu = pd.DataFrame(unknownUrls,columns=['kw1','kw1','kw1','kw1','kw1','kw1','kw1','kw1','feed','date',])
        # uu.to_csv('unknownUrls.csv', index=False)
        uu.to_sql( 'fb_kws_others',
            con=scraperEngine,
            index=False,
            if_exists='append',
            chunksize=10000
        )
    if kws:
        print('[INFO] - %s keywords retrieved.' % len(kws))
        kwr = pd.DataFrame(kws,columns=['kw1','kw2','kw3','kw4','kw5','kw6','kw7','kw8','same_links'])
        kwr['date'] =datetime.strftime(datetime.now(), "%Y-%m-%d")
        kwr['different_links'] = kwr.groupby(['kw1','kw2','kw3','kw4','kw5','kw6','kw7','kw8']).cumcount() + 1
        kwr = kwr.drop_duplicates(subset=['kw1','kw2','kw3','kw4','kw5','kw6','kw7','kw8'], keep='last')
        kwr.to_csv('keywords.csv')
        kwr.to_sql(
            'fb_kws',
            con=scraperEngine,
            index=False,
            if_exists='append',
            chunksize=10000
        )
        