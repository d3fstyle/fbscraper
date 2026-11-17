# ------------------------------------------------------------------------------------------------------------ #
# [Description]: Gets urls with unknown scheme to test if they redirects to one we can use to extract keywords #
# [Inputs]: table fb_unknown_links                                                                             #
# [Outputs]: tables fb_kws_others and fb_possible_advertisers                                                  #
# ------------------------------------------------------------------------------------------------------------ #

from urllib.parse import unquote, unquote_plus, urlparse, parse_qs, urlencode, urlunparse
from config import scraperEngine, paramsOfInterest, param2Remove
from playwright.sync_api import Playwright, sync_playwright
from datetime import datetime
import pandas as pd
import time

# URL = 'https://exploretopic.com/Symptoms_Of_Multiple_Myeloma?fbclid=IwAR22znz_SMwmDm39z0taTb6GCfUmwlIGbfckZXHdcewQSRvCU0jcOYfMoLA'
# URLTHEN = 'https://signs-of-myeloma.xyz/?ctfb[id]=4478839555474172&ctfb[alias]=fb95f40bbd00bdedfa&ctfb[elp]=ViewContent&ctfb[erp]=Search&ctfb[ec]=Lead&fbclid=IwAR22znz_SMwmDm39z0taTb6GCfUmwlIGbfckZXHdcewQSRvCU0jcOYfMoLA&network=facebook&site=undefined&adtitle=multiple+myeloma+treatment+revlimid&kw1=treatment+for+stage+2+multiple+myeloma&kw2=abecma+treatment+centers&kw3=multiple+myeloma+17p+deletion+prognosis&kw4=multiple+myeloma+oral+treatment&c1=undefined&c2=undefined&c3=undefined&sub1=undefined&sub2=undefined&sub3=undefined'
#GETURLSQUERY = 'select * from fb_unknown_links'
GETURLSQUERY = 'select * from fb_ads'
DBROW = [
    'kw1', 
    'kw2',
    'kw3',
    'kw4', 
    'kw5', 
    'kw6',
    'kw7', 
    'kw8', 
    'feed',
    'date']

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

def getUnknownUrls():
    ''' Retrieves all valid pages '''
    #urls = pd.read_sql("select landing_page,advertiser,pageid from fb_ads where last_seen='2023-04-16'",scraperEngine)
    urls = pd.read_sql("select link,advertiser,advertiser_page from fb_unknown_links where date='2023-05-05'",scraperEngine)
    return urls


def removeArgs(link):
    ''' Substracts fbclid and h parameter from link '''
    parsed = urlparse(link)
    query = parse_qs(parsed.query)
    for param in param2Remove:
        query.pop(param,'')
    parsed = parsed._replace(query=urlencode(query,True))
    return urlunparse(parsed)


def cleanUrls(urls):
    ''' Applies clean function to each link '''
    urls['link'] = urls['link'].apply(removeArgs)
    #urls['landing_page'] = urls['landing_page'].apply(removeArgs)
    #urls = urls.drop_duplicates(subset='landing_page',keep='first')
    urls = urls.drop_duplicates(subset='link',keep='first')
    return urls


def checkUrl4Kw(url):
    ''' Categorizes url and extract keywords if scheme recognized'''
    feed = ''
    row = []
    decodedUrl = unquote_plus(url)
    decodedUrl = removeArgs(decodedUrl)
    #print(decodedUrl)
    parsed = urlparse(decodedUrl)
    query = parse_qs(parsed.query)
    ks = list(query.keys())
    for key in ks:
        if key.startswith(paramsOfInterest['sedo']):
            feed = 'sedo'
            res = recoverKw[feed](decodedUrl)
            if res:
                row.append(res)
            break
        elif key.startswith(paramsOfInterest['iac']):
            feed = 'iac'
            res = recoverKw[feed](decodedUrl)
            if res:
                row.append(res)
            break
        elif key.startswith(paramsOfInterest['others']):
            feed = 'others'
            res = recoverKw[feed](decodedUrl)
            if res:
                row.append(res)
            break
        else:
            continue
    return row


def saveToDb(recoveredLinks):
    ''' Uploads keywords to database '''
    dfLinks = pd.DataFrame(recoveredLinks, columns=[
        'kw1', 
        'kw2',
        'kw3',
        'kw4', 
        'kw5', 
        'kw6',
        'kw7', 
        'kw8',
        'feed',
        'date'])
    dfLinks.to_sql(
        'fb_kws_others',
        con=scraperEngine,
        index=False,
        if_exists='append',
        chunksize=10000
    )


def saveAdvertisers(advertiserList):
    ''' Uploads recovered advertisers to database '''
    dfAdvertisers = pd.DataFrame(advertiserList, columns=['advertiser','page'])
    dfAdvertisers.drop_duplicates(inplace=True)
    dfAdvertisers.to_sql(
        'fb_possible_advertisers',
        con=scraperEngine,
        index=False,
        if_exists='append',
        chunksize=10000
    )


def run(playwright: Playwright) -> None:
    ''' Main '''
    #recovered = []
    #possibleAdvertisers = []

    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    urls = getUnknownUrls()
    urls = cleanUrls(urls)
    totalCount = len(urls)
    counter = 0
    for index, entry in urls.iterrows():
        #url = entry['landing_page']
        url = entry['link']
        row = checkUrl4Kw(url)
        if row:
            #print('\r[INFO] - Row (directly): %s\n%s url' % (row,url))
            saveToDb(row)
        else:
            try:
                page.goto(url)
            except Exception as e:
                print('\r[ERROR] - Url not valid: %s\n%s' %(url,e))
            else:
                time.sleep(7)
                try:
                    currentUrl = page.evaluate('() => document.location.href')
                except Exception as e:
                    print('\r[ERROR] - Failed to evaluate url: %s\n%s' %(url,e))
                else:
                    row = checkUrl4Kw(currentUrl)
                    if row:
                        #print('\r[INFO] - Row: %s\n%s url' % (row,url))
                        saveToDb(row)
                        #possibleAdvertisers.append({'advertiser':entry['advertiser'],'page':entry['advertiser_page']})
                        #saveAdvertisers([{'advertiser':entry['advertiser'],'page':entry['advertiser_page']}])
        counter += 1
        print('\r[INFO] - %s/%s' %(counter,totalCount), end=' ')

    page.close()


if __name__ == '__main__':
    with sync_playwright() as playwright:
        run(playwright)
