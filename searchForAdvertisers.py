# ----------------------------------------------------------------------------------- #
# [Description]: Scraping Meta Ads Library for advertisers by searching with keywords #
# [Inputs]: Meta Ads Library page, searchQueries variable                             #
# [Outputs]: tables fb_sedolinks, fb_unknown_links                                    #
# ----------------------------------------------------------------------------------- #

from urllib.parse import unquote, urlparse, parse_qs, urlencode, urlunparse
from playwright.sync_api import Playwright, sync_playwright
from config import scraperEngine, FB_PASS, FB_USER, paramsOfInterest, param2Remove
from sendNewFanPages import run as sendEmail
from datetime import datetime, timedelta
from bs4 import BeautifulSoup as bs
import pandas as pd
import argparse
import random
import time
import yake
import re


ADLIBRARYURLBASE = 'https://www.facebook.com/ads/library/'
ADLIBRARYURL =  'https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=US&q={}&publisher_platforms[0]=facebook&start_date[min]={}&start_date[max]=&sort_data[direction]=desc&sort_data[mode]=relevancy_monthly_grouped&search_type=keyword_unordered&media_type=all'
#ADLIBRARYURL =  'https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=US&q={}&publisher_platforms[0]=facebook&start_date[min]={}&start_date[max]=&sort_data[direction]=desc&sort_data[mode]=relevancy_monthly_grouped&search_type=keyword_exact_phrase&media_type=all'
#ADLIBRARYURL = 'https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q={}&publisher_platforms[0]=facebook&start_date[min]=2022-01-01&start_date[max]=&sort_data[direction]=desc&sort_data[mode]=relevancy_monthly_grouped&search_type=keyword_unordered&media_type=all'

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

GETPAGESQUERY = '''SELECT pageid FROM fb_pages WHERE valid = 1'''

ADLIMIT = 500
EEOL = '\033[K'  # For printing in the same line clearing the previous one 

searchQueriesHealth = [
    # 'The Most Common Sign',
    # 'Early Symptoms',
    'Early Signs Of',
    # 'signs of',
    # 'Symptoms of',
    # 'what is the cause of',
    # 'the real cause of',
    # 'disease is',
    # 'treatment for',
    'Heart Disease',
    'Colorectal Cancer',
    'Pancreatic Cancer',
    'Alzheimer',
    'Heart Failure',
]

searchQueriesGeneric = [
    'Search for',
    'finds',
    # 'Look',
    'Look for',
    # 'Find',
    # 'Seek',
    # 'Results',
    # 'Resources',
    # 'Information'
    # 'Busca',
    # 'Trova',
    # 'Cerca',
    # 'Trouvez',
    # 'Cherchez'
    # 'Procura',
    # 'Procurando'
]

searchQueriesTest = [
    'backyard',
    'sale of',
    'travel',
    'limited offer',
    'mower',
]

searchQueries = {
    'health':searchQueriesHealth,
    'generic':searchQueriesGeneric,
    'test':searchQueriesTest,
}

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

advertiserDict = {}

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

def saveToDb(rows):
    ''' Save ads in database '''
    ads = pd.DataFrame(rows,
            columns=[
            'landing_page',
            'advertiser',
            'advertiser_page',
            'last_seen'
            ])
    ads.drop_duplicates(inplace=True)
    for attempt in range(3):
        try:
            ads.to_sql(
                'fb_sedolinks',
                con=scraperEngine,
                index=False,
                if_exists='append',
                chunksize=10000
            )
            break
        except Exception as e:
            print('[ERROR] - Failed to upload: %s\n\tRetrying...' %e)

def saveToDbLite(rows):
    ''' Save ads in database '''
    ads = pd.DataFrame(rows,
            columns=[
            'keyword1',
            'keyword2',
            'keyword3',
            'copy',
            'link',
            'date'
            ])
    ads.drop_duplicates(inplace=True)
    for attempt in range(3):
        try:
            ads.to_sql(
                'fb_ads_gross',
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

def checkIfUrlFromAdvertiser(url):
    ''' Checks parameters to filter advertiser type urls'''
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    keys = list(query.keys())
    if any(item in keys for item in paramsOfInterest['all']):
        for param in param2Remove:
            query.pop(param,'')
        parsed = parsed._replace(query=urlencode(query,True))
        return urlunparse(parsed)
    return False


def makeScroll(page):
    ''' Scroll multiple times to load more ads.'''
    page.mouse.wheel(0, 15000)
    time.sleep(randomWait(4.4,7.8))


def savePossibleAdvertisers():
    ''' Stores in db advertisers found '''
    adDf = pd.DataFrame(advertiserDict.items(), columns=['advertiser','page'])
    if not adDf.empty:
        adDf.to_sql(
            'fb_possible_advertisers',
            con=scraperEngine,
            index=False,
            if_exists='append',
            chunksize=10000
        )

def run(playwright: Playwright, vertical, keyword, limit, anonymous) -> None:
    ''' Main '''

    queriesToUse = []
    if keyword:
        queriesToUse.append(keyword)
    else:
        queriesToUse = searchQueries.get(vertical, [])
    if queriesToUse:
        browser = playwright.chromium.launch(headless=False)
        #context = browser.new_context()
        adlimit = int(limit or ADLIMIT)
        
        lang = "en"
        max_ngram_size = 3
        deduplication_thresold = 0.55
        deduplication_algo = 'jaro'
        windowSize = 1
        numOfKeywords = 5
        kwext = yake.KeywordExtractor(lan=lang,n=max_ngram_size,dedupLim=deduplication_thresold,dedupFunc=deduplication_algo,windowsSize=windowSize,top=numOfKeywords)

        date = datetime.strftime(datetime.now(), "%Y-%m-%d")
        fromdate = datetime.strftime(datetime.now() - timedelta(days=30), "%Y-%m-%d")
        #page = context.new_page()
        page = browser.new_page()
        
        page.goto(ADLIBRARYURLBASE)
        allowCookies(page)
        if not anonymous:
            loginInLibrary(page) # if answer == 'no' else print('[INFO] - Acting as logged in.')
        input('[INFO] - Press enter when ready...')
        
        for query in queriesToUse:
            rows = []
            print('[INFO] - Query: %s' % query)
            page.goto(ADLIBRARYURL.format(query,fromdate))
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
                                    kws = kwext.extract_keywords(adCopy)
                                adProperties = div.findAll('div', attrs={'class':ADCARDPROPERTIES})
                                fieldCount = len(adProperties)
                                adId = adProperties[3].find('span').text.split(' ')[-1] if fieldCount == 4 else adProperties[4].find('span').text.split(' ')[-1]
                                if adId in knownIds:
                                    knownCount += 1
                                else:
                                    knownIds.append(adId)
                                    
                                    linkTag = div.find('a', attrs={'class':ADLINK})
                                    if linkTag:
                                        try:
                                            landingPage = unquote(unquote(linkTag['href']))
                                            landingPage = landingPage.replace('https://l.facebook.com/l.php?u=','')

                                            parsed = checkIfUrlFromAdvertiser(landingPage)
                                            if parsed:
                                                #advertiserDict[advertiser] = advertiserPage
                                                try:
                                                    scraperEngine.execute(f'''insert into `fb_possible_advertisers` (advertiser,page,foundFromQuery,date) values ("{advertiser}","{advertiserPage}","{query}","{date}")''')
                                                    print('\r[INFO] - Added [ %s | %s ].' % (advertiser,advertiserPage))
                                                except Exception as e:
                                                    print('\r[ERROR] - Failed to insert in db. (%s) Already in database?.' % advertiser)
                                                # rows.append({
                                                #     'keyword1':kws[0][0],
                                                #     'keyword2':kws[1][0],
                                                #     'keyword3':kws[2][0],
                                                #     'copy':adCopy,
                                                #     'link':parsed,
                                                #     'date':date
                                                #     }
                                                # )
                                        except Exception as e:
                                            print('\n[ERROR] - No landing page (ad not showing creative): %s' % e)
                                            continue    
                                    count += 1
                                    if limit > 0 and count == adlimit:
                                        break
                    print('\r[INFO] - %s ads processed for query [%s].' % (count, query), end=EEOL)
                    if rows:
                        # print('[INFO] - Uploading %s rows left to db.' % len(rows))
                        # saveToDbLite(rows)
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
                # print('[INFO] - Uploading %s rows left to db.' % len(rows))
                # saveToDbLite(rows)
                rows=[]
            else:
                print('[Query [%s] has no ads left.]' % query)
            time.sleep(randomWait(8.1,13.6))
            #-- End of ad card loop
        #-- End of url loop
        #context.close()
        #savePossibleAdvertisers()
        browser.close()
    else:
        print('[ERROR] - No query list for vertical (%s). Available lists: %s' % (vertical,list(searchQueries.keys())))



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Scrap ads from Meta Ad Library browser."
    )
    parser.add_argument("--limit", type=str, help="Maximum number of ads to be scraped.")
    parser.add_argument("--anonymous", action='store_true', help="Without login. Page won't show age sensitive ads.")
    parser.add_argument("--noemail", action='store_true', help="No send emails when done.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--vertical',type=str)
    group.add_argument('--keyword',type=str)
    args = parser.parse_args()
    limit = int(args.limit) if args.limit is not None else 0
    keyword = args.keyword if args.keyword is not None else ''
    vertical = args.vertical if args.vertical is not None else ''
    
    with sync_playwright() as playwright:
        run(playwright, vertical, keyword, limit, args.anonymous)
    if not args.noemail:
        sendEmail()