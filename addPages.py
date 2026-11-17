# ------------------------------------------------------------------------------------------------ #
# [Description]: Adds new pages to db by comparing db with given list and upload only the new ones #
# [Inputs]: pages2add list and fb_pages table                                                      #
# [Outputs]: tables fb_pages                                                                       #
# ------------------------------------------------------------------------------------------------ #

import pandas as pd
from config import scraperEngine

pages2add = [
'https://www.facebook.com/Smarter-Search-104419721015251',
'https://www.facebook.com/Health-Search-Online-109764684059841',
'https://www.facebook.com/healthifyer-106331095460322',
'https://www.facebook.com/Find-Info-Today-108763968730408',
'https://www.facebook.com/Search-Symptomfind-102131932403342',
'https://www.facebook.com/Health-Wealth-100622462239779',
'https://facebook.com/explore-options-trends-103109818951228',
'https://www.facebook.com/Deals-Inside-105904012430031',
'https://www.facebook.com/healthhacks411-107792305221610',
'https://facebook.com/answered-questions-103585885699687',
'https://facebook.com/wow-low-price-101348372354845',
'https://www.facebook.com/WellnessWisdomForYou-105372919157647',
'https://facebook.com/diabetes-insights-105006168003096',
'https://www.facebook.com/Search-Discover-103128775976983',
'https://facebook.com/BodyHacks4U-1764934337067780',
'https://facebook.com/YourHolisticHealthWellness-108587032132684',
'https://facebook.com/smart-tips-101162346284171',
'https://www.facebook.com/thedailybulb-2013840935535044',
'https://facebook.com/prodealscout-110994395077519',
'https://facebook.com/answer-quest-110154501988377',
'https://facebook.com/standard-solutions-106251282382674',
'https://www.facebook.com/HealthTwentyFourSevenBaby-487100844825064',
'https://facebook.com/your-health-updates-112357425093428',
'https://facebook.com/unique-solutions-114334658212391',
'https://www.facebook.com/searchsmartdeals-645274572277145',
'https://www.facebook.com/Health-Safeonline-107160205081040',
'https://www.facebook.com/Jackson-County-IN-100896332178841',
'https://facebook.com/ColumbiaPsychiatry-153587491342447',
'https://www.facebook.com/Martin-County-KY-103827705214571',
'https://www.facebook.com/Explore-to-Find-104139522540906'
]

def getRows(url):
    ''' Extracts page id from url if possible '''
    alreadyInDb = pd.read_sql('select url,pageid,feed,valid,pending from fb_pages',scraperEngine)
    #print(alreadyInDb)
    res = []
    for link in url:
        id = link.split('-')[-1]
        if id and str(id).isnumeric():
            pass
        else:
            id = link.split('id=')[-1]
        res.append({'url':link,'pageid':id,'feed':'others','valid':1,'pending':1})
    base = pd.DataFrame(res, columns=['url','pageid','feed','valid','pending'])
    newPages = pd.merge(base, alreadyInDb, indicator=True, how='outer')
    newPages.drop_duplicates(subset=['pageid'],keep=False, inplace=True)
    newPages = newPages.query('_merge=="left_only"').drop('_merge', axis=1)
    #print(newPages)
    return newPages
    

pages = getRows(pages2add)
pagesDf = pd.DataFrame(pages, columns=['url','pageid','feed','valid','pending'])

pagesDf.to_sql(
    'fb_pages',
    con=scraperEngine,
    index=False,
    if_exists='append',
    chunksize=10000
)