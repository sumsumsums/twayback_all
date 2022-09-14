from multiprocessing.dummy import Semaphore
import colorama
import requests
import platform
import argparse
import bs4
import asyncio
import sys
import re
import urllib3
from colorama import Fore, Back
from requests_futures.sessions import FuturesSession
from concurrent.futures import as_completed
from tqdm import tqdm
from time import sleep
from pathlib import Path
from playwright.sync_api import sync_playwright
from aiohttp import ClientSession, TCPConnector
import asyncio

# global variables
accounts = []
basedir = '.'
max_trials = 10
download_text = False
download_html = False
download_scrn = False
download_all  = False
overwrite_file = False

regex_tweet_ext1 = re.compile('.*TweetTextSize TweetTextSize--jumbo.*')

# account specific variables
account_name = ''
account_url = ''
wayback_cdx_url = ''
targetdir = basedir
filename_text = ''
filename_csv = ''
futures_retry = {}

# checks the status of a given url
async def checkStatus(url, session: ClientSession, sem: asyncio.Semaphore):

    async with sem:
        async with session.get(url) as response:
            return url, response.status


# controls our async event loop
async def asyncStarter(url_list, semaphore_size):
    # this will wrap our event loop and feed the the various urls to their async request function.
    status_list = []
    headers = {'user-agent':'Mozilla/5.0 (compatible; DuckDuckBot-Https/1.1; https://duckduckgo.com/duckduckbot)'}

    # using a with statement seems to be working out better
    async with ClientSession(headers=headers) as a_session:
        # limit to 50 concurrent jobs
        sem = asyncio.Semaphore(semaphore_size)
        # launch all the url checks concurrently as coroutines
        # where is the session variable coming from??? is it the global one I defined above?
        # function is expecting an async session?
        status_list = await asyncio.gather(*(checkStatus(u, a_session, sem) for u in url_list))
    # return a list of the results
    return status_list

def parse_parameter():
    # Parse arguments passed in from command line
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', required=True, default='')
    parser.add_argument('-from', '--fromdate', required=False, default='')
    parser.add_argument('-to', '--todate', required=False, default='')
    parser.add_argument('--batch-size', type=int, required=False, default=100, help="How many urls to examine at once. Between 1 and 100")
    parser.add_argument('--semaphore-size', type=int, required=False, default=50, help="How many urls(from --batch-size) to query at once. Between 1 and 50", dest='semaphore-size')
    parser.add_argument('--download-text', default=True, action=argparse.BooleanOptionalAction, dest='download-text')
    parser.add_argument('--download-html', default=True, action=argparse.BooleanOptionalAction, dest='download-html')
    parser.add_argument('--download-screenshot', default=False, action=argparse.BooleanOptionalAction, dest='download-screenshot')
    parser.add_argument('--download-all', default=False, action=argparse.BooleanOptionalAction, dest='download-all')
    parser.add_argument('--overwrite-files', default=False, action=argparse.BooleanOptionalAction, dest='overwrite-files')
    parser.add_argument('--output-directory', required=False, default='.', dest='outdir')

    args = vars(parser.parse_args())
    global accounts
    accounts.append(args['username'])

    global from_date_arg
    from_date_arg = args['fromdate']
    global to_date_arg
    to_date_arg = args['todate']

    global batch_size
    batch_size = args['batch_size']

    global semaphore_size
    semaphore_size = args['semaphore-size']

    remove_list = ['-', '/']
    global from_date
    from_date = from_date_arg.translate({ord(x): None for x in remove_list})
    global to_date
    to_date = to_date_arg.translate({ord(x): None for x in remove_list})

    global headers
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; DuckDuckBot-Https/1.1; https://duckduckgo.com/duckduckbot)'}

    global basedir
    outdir  = args['outdir']
    basedir = f"{outdir}"

    global download_all
    download_all = args['download-all']

    global download_scrn
    download_scrn = args['download-screenshot']

    global download_text
    download_text = args['download-text']

    global download_html
    download_html = args['download-html']

    global overwrite_file
    overwrite_file = args['overwrite-files']

    global futures_retry
    futures_retry = {}

# set basic variables for account
def set_account_variables():

    global targetdir
    targetdir = f"{basedir}{account_name}/"

    global account_url
    account_url = f"https://twitter.com/{account_name}"

    global wayback_cdx_url
    wayback_cdx_url = f"https://web.archive.org/cdx/search/cdx?url=twitter.com/{account_name}/status" \
                      f"&matchType=prefix&filter=statuscode:200&mimetype:text/html&from={from_date}&to={to_date}"

    set_filename()

# set filenames for account
def set_filename():
    global filename_csv
    filename_csv = f"{targetdir}result_text.csv"

# check if twitter reachable
def check_twitter():
    if download_all != True:
        account_response = requests.get(account_url, headers=headers, allow_redirects=False)
        status_code = account_response.status_code

        if status_code == 200:
            print(Back.GREEN + Fore.WHITE + f"Account is ACTIVE")
        elif status_code == 302:
            print(Back.RED + Fore.WHITE + f"Account is SUSPENDED. This means all of {Back.WHITE + Fore.RED + account_name + Back.RED + Fore.WHITE}'s Tweets will be  downloaded.")
        elif status_code ==429:
            print(Back.RED + Fore.WHITE + f"Respose Code 429: Too Many Requests. Your traffic to Twitter is being limited and results of this script will not be accurate")
        else:
            print(Back.RED + Fore.WHITE + f"No one currently has this handle. Twayback will search for a history of this handle's Tweets.")
        sleep(1)

# get list from wayback
def get_wayback_list():
    cdx_page_text = requests.get(wayback_cdx_url).text

    if len(re.findall(r'Blocked', cdx_page_text)) != 0:
        print(f"Sorry, no deleted Tweets can be retrieved for {account_name}.\n"
              f"This is because the Wayback Machine excludes Tweets for this handle.")
        sys.exit(-1)

    # Capitalization does not matter for twitter links. Url parameters after '?' do not matter either.
    # create a dict of {twitter_url: wayback_id}
    global tweet_id_and_url_dict
    tweet_id_and_url_dict = {line.split()[2].lower().split('?')[0]: line.split()[1] for line in cdx_page_text.splitlines()}

# get status of tweets
def get_tweets_status():
# create a list of just twitter urls
    twitter_url_list = []
    for url in tweet_id_and_url_dict:
        twitter_url_list.append(url)

    # break out url list in to chunks of 100 and check asyncronously
    results_list = []
    counter = 0
    for x in tqdm(range(0, len(twitter_url_list))):
        if counter==batch_size or x == len(twitter_url_list)-1 :
            results_list.extend(asyncio.run(asyncStarter(twitter_url_list[x-batch_size:x], semaphore_size)))
            counter = 0
        counter += 1

    # list of just missing twitter url
    missing_tweet_list = []
    for result in results_list:
        if result[1] == 404:
            missing_tweet_list.append(str(result[0]))
        if result[1] == 429:
            print("Respose Code 429: Too Many Requests. Your traffic to Twitter is being limited and results of this script will not be accurate")

    # list of wayback ids for just missing tweets
    global wayback_id_list
    for url in missing_tweet_list:
        wayback_id_list.append(tweet_id_and_url_dict[url])

# fill list of wayback urls to request
def fill_wayback_url_list():
    global wayback_id_list
    wayback_id_list = []

    if download_all != True:
        get_tweets_status()
    else:
        for url in tweet_id_and_url_dict:
            wayback_id_list.append(tweet_id_and_url_dict[url])

    global wayback_url_dict
    wayback_url_dict = {}
    for url, number in zip(tweet_id_and_url_dict, wayback_id_list):
        tweeturl = f"https://web.archive.org/web/{number}/{url}"
        wayback_url_dict[number] = tweeturl

    if overwrite_file == False:
        url_dict = wayback_url_dict.copy()
        for number, url in tqdm(url_dict.items(), position=0, leave=True):
            filename = get_filename_for_tweet_number(number, 'html', False)
            path = Path(filename)
            if path.is_file() == True:
                wayback_url_dict.pop(number)

    return len(wayback_url_dict)

# ask for download type (can be removed, parameter)
def ask_download_type():
    global download_text
    global download_html
    global download_scrn
    if download_text == True or download_html == True or download_scrn == True:
        return

    download_type = input(f"\nWould you like to download the Tweets, get their text only, both, or take screenshots?\nType 'download' or 'text' or 'both' "
                          f"or 'screenshot'. Then press Enter. \n").lower()

    if download_type == 'download' or download_type == 'both':
    	download_html = True
    if download_type == 'text' or download_type == 'both':
        download_text = True
    if download_type == 'screenshot':
        download_scrn = True

# get filename for tweet number
def get_filename_for_tweet_number(tweet_number, extension, create_dir):
    #20220830120945
    tweet_str   = str(tweet_number)
    tweet_date  = tweet_str[:6]
    tweet_year  = tweet_date[:4]
    tweet_month = tweet_date[-2:]
    tweet_dir   = f"{targetdir}{tweet_year}/{tweet_month}/"

    if create_dir == True:
        directory = Path(tweet_dir)
        directory.mkdir(exist_ok=True, parents=True)

    filename = f"{tweet_dir}{tweet_number}.{extension}"

    return filename

# get filename for textfile for tweets
def get_filename_for_textfile(tweet_number):
    #20220830120945
    tweet_str   = str(tweet_number)
    tweet_date  = tweet_str[:6]
    tweet_year  = tweet_date[:4]
    tweet_month = tweet_date[-2:]
    text_dir   = f"{targetdir}text/"

    directory = Path(text_dir)
    directory.mkdir(exist_ok=True, parents=True)

    filename = f"{text_dir}tweets_{tweet_year}_{tweet_month}.txt"

    return filename

# download tweet as screenshots
def tweet_download_image(url_dict):
    wayback_screenshots = {}
    screenshot_futures = []

    for number, url in url_dict.items():
        # Gets the oldest version saved
        link = f"https://archive.org/wayback/available?url={url}&timestamp=19800101"
        response1 = requests.get(link)
        jsonResponse = response1.json()
        wayback_url_screenshot = jsonResponse['url']
        # Example:
        # https://web.archive.org/web/20211108191302/https://accentusoft.com/
        # We want it like this, to remove the Wayback snapshots header:
        # https://web.archive.org/web/20211108191302if_/https://accentusoft.com/
        wayback_url_screenshot_parts = wayback_url_screenshot.split('/')
        wayback_url_screenshot_parts[4] += 'if_'
        wayback_url_screenshot = '/'.join(wayback_url_screenshot_parts)
        wayback_screenshots[number] = wayback_url_screenshot

    print('Taking screenshots...')
    sleep(1)
    print("This might take a long time depending on your Internet speed\nand number of Tweets to screenshot.")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (compatible; DuckDuckBot-Https/1.1; https://duckduckgo.com/duckduckbot)'
        )
        page = context.new_page()
        for number, tweet_to_screenshot in tqdm(wayback_screenshots.items(), position=0):
            page.goto(tweet_to_screenshot, wait_until='domcontentloaded', timeout=0)
            filename = get_filename_for_tweet_number(number, 'png', True)
            page.locator('.TweetTextSize--jumbo').screenshot(
                path={filename})

        context.close()
        browser.close()



# download tweet as text / html - repeated after error
def tweet_download_text_repeat(trials):
    trials = trials - 1.
    if trials < 0:
      	return False

    global headers
    global futures_retry

    error_occured = False
    futures = {}

    with FuturesSession(max_workers=4) as session:
        for number, url in tqdm(futures_retry.items(), position=0, leave=True):
            futures[number] = session.get(url, headers=headers, timeout=30)

    for completed_future_number, completed_future in tqdm(futures.items(),
                                                          position=0, leave=True):
        try:
            filename = get_filename_for_tweet_number(completed_future_number, 'html', True)
            with open({filename}, 'wb') as f:
                f.write(completed_future.result().content)
            futures_retry.pop(completed_future_number)
        except Exception:
            error_occured = True
            sleep(1)

    if error_occured == True:
        return tweet_download_text_repeat(trials)

    return error_occured

def find_text_in_tweet(result):
    try:
        tweet = bs4.BeautifulSoup(result.content, "lxml").find("p", {"class": regex_tweet_ext1})
        if tweet != None:
            return tweet.getText()

        tweet = bs4.BeautifulSoup(result.content, "html.parser").find(attrs={"data-testid": "tweetText"})
        if tweet != None:
            return tweet.getText()

    except AttributeError as att:
        print(att)

# download tweet as text / html
def tweet_download_text(url_dict):
    futures = {}
    dont_spam_user = False

    global futures_retry
    futures_retry.clear()

    error_occured = False

    with FuturesSession(max_workers=4) as session:
        for number, url in tqdm(url_dict.items(), position=0, leave=True):
            futures[number] = session.get(url, headers=headers, timeout=30)

    for completed_future_number, completed_future in tqdm(futures.items(), position=0, leave=True):
        result = None
        try:
            result = completed_future.result()

            if download_text == True:
                tweet = find_text_in_tweet(result)
                if tweet != None and tweet != '':
                    filename = get_filename_for_textfile(completed_future_number)
                    with open(f"{filename}", 'a') as f:
                        f.write(str(result.url.split('/', 5)[:-1]) + " " + tweet + "\n\n---\n\n")

            if download_html == True:
                filename = get_filename_for_tweet_number(completed_future_number, 'html', True)
                with open(f"{filename}", 'wb') as f:
                    f.write(result.content)

        except AttributeError as att:
            print(att)
        except Exception as exp:
            print(exp)
            if not dont_spam_user:
                print("\n\nThere is a problem with the connection.\n")
                sleep(0.5)
                print("Either the Wayback Machine is down or it's refusing the requests.\n"
                      "Your Wi-Fi connection may also be down.")
                sleep(1)
                print("Retrying...")
                # Make sure that cascading failures don't spam text on the terminal.
                dont_spam_user = True

            if result is not None:
                error_occured = True
                futures_retry[completed_future_number] = result.url

    if error_occured == True:
        error_occured = tweet_download_text_repeat(max_trials)

# download tweet
def download_for_tweets(url_dict):
    global filename_csv

    with open(f"{filename_csv}", "a") as fcsv:
        for twid in url_dict:
            url = url_dict[twid]
            fcsv.write(f'{twid},{url}\n')

    if download_scrn == True:
        tweet_download_image(url_dict)

    if download_text == True or download_html == True:
        tweet_download_text(url_dict)

# download tweet
def download_call():

    directory = Path(targetdir)
    directory.mkdir(exist_ok=True, parents=True)

    url_dict = {}
    counter = 0
    for number, url in tqdm(wayback_url_dict.items(), position=0, leave=True):
        counter = counter + 1
        url_dict[number] = url
        if counter > 100:
            download_for_tweets(url_dict)
            url_dict.clear()
            counter = 0

    if len (url_dict) > 0:
        download_for_tweets(url_dict)
        url_dict.clear()

    if download_html == True:
        print(f"\nAll Tweets have been successfully downloaded!\nThey can be found as HTML files inside the folder "
              f"{Back.MAGENTA + Fore.WHITE + targetdir + Back.BLACK + Fore.WHITE}.")

    if download_text == True:
        print(f"\nA text file is saved, which lists all URLs for the deleted Tweets and "
              f"their text, has been saved.\nYou can find it inside the folder "
              f"{Back.MAGENTA + Fore.WHITE + targetdir + Back.BLACK + Fore.WHITE}.")

    if download_scrn == True:
        print(f"Screenshots have been successfully saved!"
              f"\nYou can find screenshots inside the folder "
              f"{Back.MAGENTA + Fore.WHITE + targetdir + Back.BLACK + Fore.WHITE}.")

# set parameters
colorama.init(autoreset=True)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

parse_parameter()

# ask for download type if not set yet
ask_download_type()

# process all accounts
for account in accounts:
    account_name = account

    set_account_variables( )

    # check twitter acccount
    check_twitter()

    # request wayback machine
    get_wayback_list()

    # fill wayback urls
    number_tweets = fill_wayback_url_list()

    if number_tweets > 0:
        # download call
        download_call()
    else:
        print(f"No tweets to download for {account_name}")

print(f"Program finished")
