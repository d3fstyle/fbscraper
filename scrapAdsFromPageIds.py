# ----------------------------------------------------------------------------------- #
# [Description]: Scraping Meta Ads Library from fan pages' ids to search for keywords #
# [Inputs]: Meta Ads Library page, page ids                                           #
# [Outputs]: tables raw_fb_ads, fb_ads_filtered                                       #
# ----------------------------------------------------------------------------------- #

from distutils.command.clean import clean
from config import scraperEngine, FB_PASS, FB_USER, paramsOfInterest, param2Remove
from urllib.parse import unquote, urlparse, parse_qs, urlencode, urlunparse
from playwright.sync_api import Playwright, sync_playwright
from datetime import datetime, timedelta
from sendResume import run as sendEmail
from bs4 import BeautifulSoup as bs
from methods import *
import pandas as pd
import argparse
import random
import time
import yake

MAX_TIMEOUT = 60000

ADLIBRARYURLBASE = 'https://www.facebook.com/ads/library/'
ADLIBRARYURL = 'https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={}&view_all_page_id={}&sort_data[direction]=desc&start_date[min]={}&start_date[max]=&sort_data[mode]=relevancy_monthly_grouped&search_type=page&media_type=all'
FBADREDIRECT = 'https://l.facebook.com/l.php?u='

#-- CSS classes --#
ADCARD = '_7jvw x2izyaf x1hq5gj4 x1d52u69'
ADCARDPROPERTIES = 'x3nfvp2 x1e56ztr'
ADCOPY = '_7jyr _a25-'
ADLINK = 'x1hl2dhg x1lku1pv x8t9es0 x1fvot60 xxio538 xjnfcd9 xq9mrsl x1yc453h x1h4wwuj x1fcty0u x1lliihq'
ADFOOTER = '_8jgz _8jg_'
ADFOOTERELEMENTS = '_4ik4 _4ik5'
ADVERTISERLOGO = '_8nqq img'
ADVERTISERLINK = 'xt0psk2 x1hl2dhg xt0b8zv x8t9es0 x1fvot60 xxio538 xjnfcd9 xq9mrsl x1yc453h x1h4wwuj x1fcty0u'
#-----------------#

GETPAGESQUERY = '''SELECT * FROM fb_pages WHERE pending = 1'''

ADLIMIT = 900
EEOL = '\033[K'  # For printing in the same line clearing the previous one 

months = {
    'JAN':'01',
    'ENE':'01',
    'FEB':'02',
    'MAR':'03',
    'APR':'04',
    'ABR':'04',
    'MAY':'05',
    'JUN':'06',
    'JUL':'07',
    'AUG':'08',
    'AGO':'08',
    'SEP':'09',
    'SEPT':'09',
    'OCT':'10',
    'NOV':'11',
    'DIC':'12',
    'DEC':'12'

}
loginFlag = False

def run_once(f):
    ''' Decorator to run only once'''
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            wrapper.has_run = True
            return f(*args, **kwargs)
    wrapper.has_run = False
    return wrapper


@run_once
def allowCookiesFromPage(pageObject):
    ''' Run once for fb page '''
    pageObject.get_by_role("button", name="Allow all cookies").first.click()
    return


@run_once
def allowCookies(pageObject):
    ''' Run once for ad library site '''
    pageObject.get_by_role("button", name="Allow all cookies").first.click()
    return


def loginInLibrary(page):
    ''' login through Ads Library sign in button '''
    page.get_by_role("menuitem", name="Open navigation panel").click()
    page.get_by_role("link", name="Sign in").click()
    page.wait_for_url("https://www.facebook.com/")
    page.get_by_test_id("royal_email").fill(FB_USER)
    page.get_by_test_id("royal_email").press("Tab")
    page.get_by_test_id("royal_pass").fill(FB_PASS)
    page.get_by_test_id("royal_pass").press("Enter")
    page.wait_for_url("https://www.facebook.com/")
    loginFlag = True

# def saveToDb(rows):
#     ''' Save ads in database '''
#     ads = pd.DataFrame(rows,
#             columns=[
#             'landing_page',
#             'advertiser',
#             'advertiser_page',
#             'last_seen'
#             ])
#     ads.drop_duplicates(inplace=True)
#     for attempt in range(3):
#         try:
#             ads.to_sql(
#                 'fb_sedolinks',
#                 con=scraperEngine,
#                 index=False,
#                 if_exists='append',
#                 chunksize=10000
#             )
#             break
#         except Exception as e:
#             print('[ERROR] - Failed to upload: %s\n\tRetrying...' %e)

def saveToDb(rows, table):
    ''' Save ads in database '''
    ads = pd.DataFrame(rows,
            columns=[
            'adid',
            'seen_count',
            'copy',
            'link',
            'kw1',
            'kw2',
            'kw3',
            'kw4',
            'kw5',
            'kw6',
            'kw7',
            'kw8',
            'vertical',
            'advertiser_id',
            'advertiser_name',
            'partner',
            'date',
            ])
    ads.drop_duplicates(inplace=True)
    for attempt in range(3):
        try:
            ads.to_sql(
                table,
                con=scraperEngine,
                index=False,
                if_exists='append',
                chunksize=10000
            )
            break
        except Exception as e:
            print('[ERROR] - Failed to upload: %s\n\tRetrying...' %e)


def randomWait(first, last):
    ''' Makes random seconds to sleep '''
    return round(random.uniform(first,last),2)


def checkIfUrlIsFromSedo(url, advertiser, advertiserPage):
    ''' Get url parameters to see if it matches with SEDO scheme '''
    parsed = urlparse(url)
    values = parse_qs(parsed.query)
    if values:
        #if (values.get('ctfb[alias]',False) or values.get('ctfb[id]',False)) and values.get('kw1',False):
        if values.get('kw1',False):
            print('\r[INFO] - VALUES: %s' %str(values))
            values.pop('fblid', None)
            values.pop('h', None)
            parsed = parsed._replace(query=urlencode(values))
            link = urlunparse(parsed)
            return link
        else:
            date = datetime.strftime(datetime.now(), "%Y-%m-%d")
            scraperEngine.execute('''insert into fb_unknown_links (link,advertiser,advertiser_page,date) values ("%s","%s","%s","%s")''' % (url,advertiser,advertiserPage,date))

    return None


def checkParamsOfUrl(url):
    ''' Checks if link has params of interest '''
    res = False
    unparsed = url
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    keys = list(query.keys())
    if any(item in keys for item in paramsOfInterest['all']):
        for param in param2Remove:
            query.pop(param,'')
        parsed = parsed._replace(query=urlencode(query,True))
        unparsed = urlunparse(parsed)
        res = True
    return res, unparsed


def checkIfUrlFromAdvertiser(url, browser):
    ''' Checks parameters to filter advertiser type urls'''
    result,finalUrl = checkParamsOfUrl(url)
    if not result:
        # try to check if there is a redirect to a final page
        try:
            page = browser.new_page()
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
                page.close()                           
                result, finalUrl = checkParamsOfUrl(currentUrl)   
    return result, finalUrl


def checkPreviousRecordsOfThisAd(adId):
    ''' Counts how many times this ad appears in previous scraping sessions '''
    query = f'''select count(*) as occurrences from raw_fb_ads where adid = '{adId}' and date >= date_sub(curdate(), interval 30 day);'''
    response = scraperEngine.execute(query)
    if response:
        resDict = response.mappings().all()
        return resDict[0]['occurrences']

def makeScroll(page):
    ''' Scroll multiple times to load more ads.'''
    page.mouse.wheel(0, 15000)
    time.sleep(randomWait(4.4,7.8))


def getFanPages():
    ''' Retrieves all pending pages to scrap from '''
    response = scraperEngine.execute(GETPAGESQUERY)
    if response:
        resDict = response.mappings().all()
        return resDict
    return {}


def cleanResults(date):
    ''' Filter ads added in db to remove cloned (on copy column) '''
    print(date)
    df = pd.read_sql(f"select * from raw_fb_ads where date='{date}'",scraperEngine)
    #print(df)
    df['clones'] = 1
    df1 = df.groupby(['copy'],as_index=False).agg({
        'adid': 'last',
        'seen_count': 'last',
        'link':'last',
        'kw1':'last',
        'kw2':'last',
        'kw3':'last',
        'kw4':'last',
        'kw5':'last',
        'kw6':'last',
        'kw7':'last',
        'kw8':'last',
        'vertical':'last',
        'advertiser_id':'last',
        'advertiser_name': 'last',
        'partner':'last',
        'date':'last',
        'clones':'sum'
    })
    #print(df1[df1.duplicated('adid')])
    df1.to_csv('adsFiltered.csv')
    for attempt in range(3):
        try:
            df1.to_sql(
                'fb_ads_filtered',
                con=scraperEngine,
                index=False,
                if_exists='append',
                chunksize=10000)
            break
        except Exception as e:
            print('[ERROR] - Failed to upload filtered results: %s\n\tRetrying...' %e)

def run(playwright: Playwright, limit, anonymous) -> None:
    ''' Main '''

    browser = playwright.chromium.launch(headless=False)
    adlimit = int(limit or ADLIMIT)
    
    lang = "en"
    max_ngram_size = 3
    deduplication_thresold = 0.55
    deduplication_algo = 'jaro'
    windowSize = 1
    numOfKeywords = 5
    kwext = yake.KeywordExtractor(lan=lang,n=max_ngram_size,dedupLim=deduplication_thresold,dedupFunc=deduplication_algo,windowsSize=windowSize,top=numOfKeywords)

    date = datetime.strftime(datetime.now(), "%Y-%m-%d")
    fromdate = datetime.strftime(datetime.now() - timedelta(days=7), "%Y-%m-%d")
    page = browser.new_page()
    page.set_default_timeout(MAX_TIMEOUT)
    
    page.goto(ADLIBRARYURLBASE)
    allowCookies(page)
    if not anonymous:
        loginInLibrary(page) 
    input('[INFO] - Press enter when ready...')

    advertisers = getFanPages()
    
    for adPage in advertisers:
        rows = []
        print('[INFO] - %s [ %s | %s | %s ]' % (adPage['name'], adPage['geo'], adPage['vertical'], adPage['pageid']))
        page.goto(ADLIBRARYURL.format(adPage['geo'],adPage['pageid'],fromdate))
        #allowCookies(page)
        time.sleep(randomWait(12.1,15.4))

        count = 0
        matchedCount = 0
        adcardsBefore = 0

        content = page.content()
        soup = bs(content, 'html.parser')
        adcards = soup.findAll('div', attrs={'class':ADCARD})

        areDifferentAds = True
        knownIds = []
        knownCount = 0
        while  (adcardsBefore != len(adcards)) and areDifferentAds:  # When they're the same, it means no more adcards are loading.
            adcards = adcards[adcardsBefore:]  # Substracts previous adcards keeping only new ones.
            
            if len(adcards) > 1:
                for div in adcards:
                    try:
                        advertiser = div.find('img', attrs={'class':ADVERTISERLOGO})['alt']
                    except:
                        pass
                    else:
                        try:
                            advertiserPage = div.find('a', attrs={'class':ADVERTISERLINK})['href']
                        except:
                            pass
                        else:
                            adCopy = ''
                            for nested in div.findAll('div', attrs={'class': ADCOPY}):
                                if nested.text:
                                    adCopy = nested.text
                            kws = []
                            if adCopy:
                                kwsX = kwext.extract_keywords(adCopy)
                            adProperties = div.findAll('div', attrs={'class':ADCARDPROPERTIES})
                            fieldCount = len(adProperties)
                            adId = adProperties[0].find('span').text.split(' ')[-1]
                            if adId in knownIds:
                                knownCount += 1
                            else:
                                print('\r\t\t-> adId: %s' % adId, end=EEOL)
                                knownIds.append(adId)
                                
                                linkTag = div.find('a', attrs={'class':ADLINK})
                                if linkTag:
                                    try:
                                        landingPage = unquote(unquote(linkTag['href']))
                                        landingPage = landingPage.replace(FBADREDIRECT,'')
                                    except Exception as e:
                                        print('\r[SKIPPED] - No landing page (ad not showing creative): %s' % e)
                                        continue 
                                    else:
                                        parseResult, finalUrl = checkIfUrlFromAdvertiser(landingPage, browser)
                                        kws = checkUrl4Kw(finalUrl)
                                        seenCounter = checkPreviousRecordsOfThisAd(adId)
                                        if parseResult and kws:
                                            rows.append({
                                                'adid':adId,
                                                'seen_count':seenCounter,
                                                'copy':adCopy,
                                                'link':finalUrl,
                                                'kw1':kws['kw1'],
                                                'kw2':kws['kw2'],
                                                'kw3':kws['kw3'],
                                                'kw4':kws['kw4'],
                                                'kw5':kws['kw5'],
                                                'kw6':kws['kw6'],
                                                'kw7':kws['kw7'],
                                                'kw8':kws['kw8'],
                                                'vertical': adPage['vertical'],
                                                'advertiser_id':adPage['pageid'],
                                                'advertiser_name': adPage['name'],
                                                'partner':kws['feed'],
                                                'date':date
                                                }
                                            )
                                       
                                count += 1
                                if limit > 0 and count == adlimit:
                                    break
                print('\r[INFO] - %s ads processed.' % count, end=EEOL)
                if rows:
                    print('\r[INFO] - Uploading %s rows left to db.' % len(rows))
                    saveToDb(rows, 'raw_fb_ads')
                    rows = []
                else:
                    if knownCount == len(adcards):
                        areDifferentAds=False
                knownCount = 0
                adcardsBefore += len(adcards)  # Sets the count before scrolling and load more.
                makeScroll(page)
                content = page.content()
                soup = bs(content, 'html.parser')
                adcards = soup.findAll('div', attrs={'class':ADCARD})
            else:
                areDifferentAds = False
        knownCount = 0
        knownIds = []
        if rows:
            print('\r[INFO] - Uploading %s rows left to db.' % len(rows))
            saveToDb(rows, 'raw_fb_ads')
            rows=[]
        else:
            print('\r\t\t-> No ads left.')
        time.sleep(randomWait(8.1,13.6))
        #-- End of ad card loop
    #-- End of url loop
    #context.close()
    browser.close()
    cleanResults(date)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Scrap ads from Meta Ad Library browser."
    )
    parser.add_argument("--limit", type=str, help="Maximum number of ads to be scraped.")
    parser.add_argument("--anonymous", action='store_true', help="Without login. Page won't show age sensitive ads.")
    parser.add_argument("--noemail", action='store_true', help="No send emails when done.")
    args = parser.parse_args()
    limit = int(args.limit) if args.limit is not None else 0
    with sync_playwright() as playwright:
        run(playwright,limit,args.anonymous)
    if not args.noemail:
        sendEmail()
    #cleanResults('2023-06-15')
