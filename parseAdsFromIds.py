# -------------------------------------------------------------- #
# [Description]: Get all ads from advertisers stored in database #
# [Inputs]: table fb_pages                                       #
# [Outputs]: tables fb_ads                                       #
# -------------------------------------------------------------- #

from playwright.sync_api import Playwright, sync_playwright
from urllib.parse import unquote, urlparse, parse_qs
from config import scraperEngine, FB_PASS, FB_USER
from bs4 import BeautifulSoup as bs
from datetime import datetime
import youtube_dl as you
import pandas as pd
import argparse
import random
import time
import re

ADLIBRARYURLBASE = 'https://www.facebook.com/ads/library/'
ADLIBRARYURL = 'https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&view_all_page_id={}&sort_data[direction]=desc&sort_data[mode]=relevancy_monthly_grouped&search_type=page&media_type=all'

#-- CSS classes --#
ADCARD = '_7jvw x2izyaf x1hq5gj4 x1d52u69'
ADCARDPROPERTIES = 'x3nfvp2 x1e56ztr'
ADCOPY = '_7jyr _a25-'
ADLINK = 'x1hl2dhg x1lku1pv x8t9es0 x1fvot60 xxio538 xjnfcd9 xq9mrsl x1yc453h x1h4wwuj x1fcty0u x1lliihq'
ADFOOTER = '_8jgz _8jg_'
ADFOOTERELEMENTS = '_4ik4 _4ik5'
#-----------------#

GETPAGESQUERY = '''SELECT pageid FROM fb_pages WHERE valid = 1 and pending = 1'''
ADLIMIT = 500
RESTLIMIT = 5
RESTTIME = 300

# -- For debug --
# urls=[
#     #"https://www.facebook.com/Ruby-106450588505475",
#     "https://www.facebook.com/BeOrganicallYou"
# ]
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
    pageObject.get_by_role("button", name="Only allow essential cookies").first.click()
    return


@run_once
def allowCookies(pageObject):
    ''' Run once for ad library site '''
    pageObject.get_by_role("button", name="Only allow essential cookies").first.click()
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


def loginInPage(page):
    ''' login from facebook regular site '''
    page.goto("https://www.facebook.com/")
    #page.get_by_role("button", name="Allow essential and optional cookies").click()
    page.get_by_test_id("royal_email").click()
    page.get_by_test_id("royal_email").fill(FB_USER)
    page.get_by_test_id("royal_pass").click()
    page.get_by_test_id("royal_pass").fill(FB_PASS)
    page.get_by_test_id("royal_login_button").click()
    page.wait_for_url("https://www.facebook.com/?sk=welcome")
    loginFlag = True


def getPageIdFromHtml(page, url):
    ''' Extracts page id from html (is located in multiple <script> tags within <head> section)'''
    pattern =  '{"comet_page_cards":\[],"id":"(\d+)"}'

    page.goto(url)
    #allowCookiesFromPage(page)
    content = page.content()
    soup = bs(content, 'html.parser')

    match = re.search(pattern, str(soup))
    pageId = match.group(1) #this returns only the id
    return pageId


def checkIfPageIdInUrl(url):
    ''' Extracts page id from url if possible '''
    possibleId = url.split('-')[-1]
    if possibleId and str(possibleId).isnumeric():
        return possibleId
    else:
        return False


def saveToDb(rows):
    ''' Save ads in database '''
    ads = pd.DataFrame(rows,
            columns=[
            "adid",
            "pageid",
            "landing_page",
            "adtimestamp",
            "advertiser",
            "adcopy",
            "adcreative",
            "domain",
            "feed",
            "headline",
            "description",
            "last_seen"
            ])
    for attempt in range(3):
        try:
            ads.to_sql(
                'fb_ads',
                con=scraperEngine,
                index=False,
                if_exists='append',
                chunksize=10000
            )
            break
        except Exception as e:
            print('[ERROR] - Failed to upload: %s\n\tRetrying...' %e)


def getPageIds():
    ''' Retrieves all valid pages '''
    urls = []
    response = scraperEngine.execute(GETPAGESQUERY)
    if response:
        for row in response.all():
            urls.append(row[0])
    return urls


def setPageNotValid(url):
    ''' Marks url as not valid in db '''
    scraperEngine.execute('UPDATE fb_pages SET valid = 0 WHERE url == {}'.format(url))


def saveCreativity(mediaUrl,name):
    ''' Saves to disk the creativity (image/video) '''
    options = {'outtmpl':name}
    with you.YoutubeDL(options) as u:
        u.download([mediaUrl])


def randomWait(first, last):
    ''' Makes random seconds to sleep '''
    return round(random.uniform(first,last),2)


def checkIfUrlIsFromSedo(url):
    ''' Get url parameters to see if it matches with SEDO scheme '''
    parsed = urlparse(url)
    values = parse_qs(parsed.query)
    if values:
        if values.get('kw1',False):
            #ic('\r[INFO] - VALUES: %s' %str(values))
            return True
    return False


def catalogueFeed(url):
    ''' Tries to sort url feed (SEDO, DA, etc.)'''
    if checkIfUrlIsFromSedo(url):
        return 'sedo'
    else:
        return 'unknown'


def makeScroll(page):
    ''' Scroll multiple times to load more ads.'''
    page.mouse.wheel(0, 15000)
    time.sleep(randomWait(6.4,8.8))


def run(playwright: Playwright, limit, anonymous, savemedia) -> None:
    ''' Main '''
   
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    adlimit = int(limit or ADLIMIT)
    
    date = datetime.strftime(datetime.now(), "%Y-%m-%d")
    page = context.new_page()
    
    ids = getPageIds()
    print('[INFO] - %s pages to work with.' % len(ids))

    page.goto(ADLIBRARYURLBASE)
    allowCookies(page)
    if not anonymous:
        #answer = input('[INFO] - Are we already logged in? (yes/no): ')
        loginInLibrary(page) # if answer == 'no' else print('[INFO] - Acting as logged in.')
    input('[INFO] - Press enter when ready...')

    adcardsBefore = 0
    idcount = 1
    for id in ids:
        rows = []
        print('[INFO] - Page ID %s' % id)
        page.goto(ADLIBRARYURL.format(id))
        #allowCookies(page)
        time.sleep(randomWait(6.2,8.7))
        # -- Scrolling if required  --
        # for i in range(7): #make the range as long as needed
        #     page.mouse.wheel(0, 15000)
        #     time.sleep(randomWait(2.8,4.2))
        #     i += 1
        count = 0
        content = page.content()
        soup = bs(content, 'html.parser')

        adcardsBefore = 0
        adcards = soup.findAll('div', attrs={'class':ADCARD})

        areDifferentAds = True
        knownIds = []
        knownCount = 0
        while (adcardsBefore != len(adcards)) and areDifferentAds:  # When they're the same, it means no more adcards are loading.
            adcards = adcards[adcardsBefore:]  # Substracts previous adcards keeping only new ones.
            if len(adcards) > 1:
                for div in adcards:
                    adProperties = div.findAll('div', attrs={'class':ADCARDPROPERTIES})
                    fieldCount = len(adProperties)
                    adTimestamp = adProperties[1].find('span').text  #Started running on Mar 22, 2023
                    stampItems = adTimestamp.split(' ')
                    adTimestamp = stampItems[-1]+'-'+months[stampItems[-2].upper()]+'-'+str(int(stampItems[-3].replace(',',''))).zfill(2)  # To convert to YYYY-MM-DD
                    adId = adProperties[3].find('span').text.split(' ')[-1] if fieldCount == 4 else adProperties[4].find('span').text.split(' ')[-1]
                    if adId in knownIds:
                        knownCount += 1
                    else:
                        knownIds.append(adId)

                        try:
                            advertiser = div.find('img')['alt']
                        except:
                            pass
                        else:              
                            adCopy = ''
                            for nested in div.findAll('div', attrs={'class': ADCOPY}):
                                if nested.text:
                                    adCopy = nested.text

                            linkTag = div.find('a', attrs={'class':ADLINK})
                            feed = 'unknown'
                            if linkTag:
                                try:
                                    landingPage = unquote(unquote(linkTag['href']))
                                    landingPage = landingPage.replace('https://l.facebook.com/l.php?u=','')
                                    feed = catalogueFeed(landingPage)
                                except Exception as e:
                                    # When not logged in, ads with age filter won't show.
                                    print('[ERROR] - No landing page (ad not showing creative): %s' % e)
                                    continue        
                                image = ''
                                video = ''
                                if linkTag.find('img'):
                                    try:
                                        image = linkTag.find('img')['src']
                                    except:
                                        pass
                                    else:
                                        if savemedia:
                                            saveCreativity(image,adId+'.'+image.split('.')[-1])
                                else:
                                    try:
                                        video = div.find('video')['src']
                                    except:
                                        pass
                                    else:
                                        #videoPoster = div.find('video')['poster']
                                        if savemedia:
                                            saveCreativity(video,adId+'.mp4')
                                
                                domain = ''
                                headline = ''
                                description = ''
                                for nested in div.findAll('div', attrs={'class': ADFOOTER}):
                                    elements = nested.findAll('div', attrs={'class':ADFOOTERELEMENTS})
                                    domain = elements[0].text
                                    headline = elements[1].text
                                    description = elements[2].text
                                
                                rows.append({
                                    'adid': adId,
                                    'pageid':id,
                                    'landing_page': landingPage,
                                    'adtimestamp': adTimestamp,
                                    'advertiser': advertiser,
                                    'adcopy': adCopy,
                                    'adcreative': image or video,
                                    'domain': domain,
                                    'feed': feed,
                                    'headline': headline,
                                    'description': description,
                                    'last_seen': date
                                    })
                            count += 1
                            print('\r[INFO] - %s ads processed for id "%s".' % (count, id), end=' ')
                            if limit > 0 and count == adlimit:
                                break
                
                if rows:
                    print('\n[INFO] - Uploading step: %s rows to db.' % len(rows))
                    saveToDb(rows)
                    rows = []
                else:
                    if knownCount == len(adcards):
                        areDifferentAds=False
                adcardsBefore += len(adcards)  # Sets the count before scrolling and load more.
                makeScroll(page)
                content = page.content()
                soup = bs(content, 'html.parser')
                adcards = soup.findAll('div', attrs={'class':ADCARD})
            else:
                areDifferentAds=False
        idcount+=1
        if (idcount % RESTLIMIT) == 0:
            time.sleep(RESTTIME)
        if rows:
            print('[INFO] - Uploading %s rows left to db.' % len(rows))
            saveToDb(rows)
        else:
            print('[INFO] - ID %s has no ads left.' % id)
        scraperEngine.execute('update fb_pages set pending=0 where pageid="%s"'%id)
        time.sleep(randomWait(8.1,13.6))
        #-- End of ad card loop
    #-- End of url loop
    context.close()
    browser.close()



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Scrap ads from Meta Ad Library browser."
    )
    parser.add_argument("--limit", type=str, help="Maximum number of ads to be scraped.")
    parser.add_argument("--anonymous", action='store_true', help="Maximum number of ads to be scraped.")
    parser.add_argument("--savemedia", action='store_true', help="Save media to disk.")
    args = parser.parse_args()
    limit = int(args.limit) if args.limit is not None else 0
    with sync_playwright() as playwright:
        run(playwright,limit,args.anonymous, args.savemedia)
