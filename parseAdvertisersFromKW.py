from playwright.sync_api import Playwright, sync_playwright
from config import scraperEngine, FB_PASS, FB_USER
from bs4 import BeautifulSoup as bs
from datetime import datetime
import youtube_dl as you
import pandas as pd
import argparse
import random
import time
import re

ADLIBRARYURL = 'https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q={}&sort_data[direction]=desc&sort_data[mode]=relevancy_monthly_grouped&search_type=keyword_unordered&media_type=all'

#-- CSS classes --#
ADCARD = '_7jvw x2izyaf x1hq5gj4 x1d52u69'
ADCARDPROPERTIES = 'x3nfvp2 x1e56ztr'
ADCOPY = '_7jyr _a25-'
ADLINK = 'x1hl2dhg x1lku1pv x8t9es0 x1fvot60 xxio538 xjnfcd9 xq9mrsl x1yc453h x1h4wwuj x1fcty0u x1lliihq'
ADFOOTER = '_8jgz _8jg_'
ADFOOTERELEMENTS = '_4ik4 _4ik5'
#-----------------#

GETKWQUERY = '''SELECT kw FROM fb_keywords WHERE pending = 1'''

months = {
    'Jan':'01',
    'Feb':'02',
    'Mar':'03',
    'Apr':'04',
    'May':'05',
    'Jun':'06',
    'Jul':'07',
    'Aug':'08',
    'Sep':'09',
    'Sept':'09',
    'Oct':'10',
    'Nov':'11',
    'Dec':'12'

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
def allowCookies(pageObject):
    ''' Run once for ad library site '''
    pageObject.get_by_role("button", name="Only allow essential cookies").first.click()
    return


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
            "headline",
            "description",
            "last_seen"
            ])
    ads.to_sql(
        'fb_ads',
        con=scraperEngine,
        index=False,
        if_exists='append',
        chunksize=10000
    )


def getKwToSearch():
    ''' Retrieves pending keywords to search '''
    kw = []
    response = scraperEngine.execute(GETKWQUERY)
    if response:
        for row in response.all():
            kw.append(row[0])
    return kw


def run(playwright: Playwright, limit, anonymous=False) -> None:
    ''' Main '''
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    rows = []
    date = datetime.strftime(datetime.now(), "%Y-%m-%d")
    page = context.new_page()
    
    kws = getKwToSearch()
    print('[INFO] - %s keywords to work with.' % len(kws))
    for kw in kws:
        print('[INFO] - Keyword: %s' % id)
        page.goto(ADLIBRARYURL.format(id))
        allowCookies(page)
        time.sleep(random.radint(3,6))
        # -- Scrolling if required  --
        # for i in range(1): #make the range as long as needed
        #     page.mouse.wheel(0, 15000)
        #     time.sleep(2)
        #     i += 1
        
        count = 0
        content = page.content()
        soup = bs(content, 'html.parser')
        
        for div in soup.findAll('div', attrs={'class':ADCARD}):
            adProperties = div.findAll('div', attrs={'class':ADCARDPROPERTIES})
            fieldCount = len(adProperties)
            adTimestamp = adProperties[1].find('span').text  #Started running on Mar 22, 2023
            stampItems = adTimestamp.split(' ')
            adTimestamp = stampItems[-1]+'-'+months[stampItems[-3]]+'-'+stampItems[-2].replace(',','')  # To convert to YYYY-MM-DD
            adId = adProperties[3].find('span').text.split(' ')[-1] if fieldCount == 4 else adProperties[4].find('span').text.split(' ')[-1]


            advertiser = div.find('img')['alt']
            
            adCopy = ''
            for nested in div.findAll('div', attrs={'class': ADCOPY}):
                if nested.text:
                    adCopy = nested.text

            linkTag = div.find('a', attrs={'class':ADLINK})
            print(div.text)
            try:
                landingPage = linkTag['href']
            except Exception as e:
                # When not logged in, ads with age filter won't show.
                print('[ERROR] - No landing page (ad not showing creative): %s' % e)
                continue        
            image = ''
            video = ''
            if linkTag.find('img'):
                image = linkTag.find('img')['src']
                saveCreativity(image,adId+'.'+image.split('.')[-1])
            else:
                video = div.find('video')['src']
                #videoPoster = div.find('video')['poster']
                saveCreativity(video,adId+'.mp4')
            
            domain = ''
            headline = ''
            description = ''
            for nested in div.findAll('div', attrs={'class': ADFOOTER}):
                elements = nested.findAll('div', attrs={'class':ADFOOTERELEMENTS})
                domain = elements[0].text
                headline = elements[1].text
                description = elements[2].text
                    
            print('''[INFO] - --------------\n
AdId: %s
AdTimestamp: %s
Advertiser: %s
AdCopy: %s
AdCreative: %s
Domain: %s
Landing Page: %s
Headline: %sretro 
Description: %s''' %(
                adId,adTimestamp,advertiser,adCopy,image or video,domain,landingPage,headline,description))
            rows.append({
                'adid': adId,
                'pageid':id,
                'landing_page': landingPage,
                'adtimestamp': adTimestamp,
                'advertiser': advertiser,
                'adcopy': adCopy,
                'adcreative': image or video,
                'domain': domain,
                'headline': headline,
                'description': description,
                'last_seen': date
                })
            count += 1
            if limit > 0 and count == limit:
                break

        time.sleep(10)
        #-- End of ad card loop
    #-- End of url loop
    context.close()
    browser.close()

    saveToDb(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Scrap ads from Meta Ad Library browser."
    )
    parser.add_argument("--limit", type=str, help="Maximum number of ads to be scraped.")
    parser.add_argument("--anonymous", action='store_true', help="Maximum number of ads to be scraped.")
    args = parser.parse_args()
    limit = int(args.limit) if args.limit is not None else 0
    with sync_playwright() as playwright:
        run(playwright,limit,args.anonymous)
