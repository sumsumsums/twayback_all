# Twayback All: Fork of https://github.com/Mennaruuk/twayback - Downloading all Tweets from the Wayback Machine

This is a fork of https://github.com/Mennaruuk/twayback

## Differences:
 - Can download all tweets of a user from wayback machine, not only deleted
 - Additional parameters, no need for interaction during runtime
 - Directory structure for output
   - HTML files in subdirectories by year / month
   - Text files in files by year / month 
 - Bugfixes

## Features
 - Can download some or all of a user's archived Tweets, optional only deleted
 - Lets you extract Tweets text to a text file (yes, even quote retweets!)
 - Has ability to screenshot Tweets
 - Allows custom time range to narrow search for deleted Tweets archived between two dates.
 - Saves a log of the deleted tweet URLs in case you want to view on the Wayback Machine

## TODO
 - sort Tweets in date / time order in text file (if possible date / time from tweets)
 - run for multiple accounts 
 - ...

## Usage
>    twayback -u USERNAME [OPTIONS]
    
    -u, --username                                        Specify target user's Twitter handle

    --batch-size                                          Specify how many URLs you would like to 
                                                          examine at a time. Expecting an integer between
                                                          1 and 100. A larger number will give you a speed
                                                          boost but at the risk of errors. Default = 100

    --semaphore-size                                      Specify how many urls from --batch-size you would 
                                                          like to query asyncronously at once. Expecting an integer
                                                          between 1 and 50. A larger number number will give you a speed
                                                          boost but at the risk of errors. Default = 50
    
    -from, --fromdate                                     Narrow search for Tweets *archived*
                                                          on and after this date
                                                          (can be combined with -to)
                                                          (format YYYY-MM-DD or YYYY/MM/DD
                                                          or YYYYMMDD, doesn't matter)
                                            
    -to, --todate                                         Narrow search for Tweets *archived*
                                                          on and before this date
                                                          (can be combined with -from)
                                                          (format YYYY-MM-DD or YYYY/MM/DD
                                                          or YYYYMMDD, doesn't matter)
    --download-text, --no-download-text                   Download as text file

    --download-html, --no-download-html                   Downlaod as HTML file

    --download-scrn, --no-download-scrn                   Take screenshots of tweets

    --download-all, --no-download-all                     Download all tweets, not only deleted (Default: all)

    --overwrite-files, --no-overwrite-files               Download tweets, even so a HTML file of it already exists

    --output-directory                                    Directory to save all output in a subdirectory "username" (Default: current)
    
    Examples:
    twayback -u taylorswift13                             Downloads all of @taylorswift13's
                                                          deleted Tweets
    
    twayback -u jack -from 2022-01-05                     Downloads all of @jack's
                                                          deleted Tweets
                                                          *archived* since January 5,
                                                          2022 until now
    
    twayback -u drake -to 2022/02/09                      Downloads all of @drake's
                                                          deleted Tweets *archived*
                                                          since the beginning until
                                                          February 9, 2022
    
    twayback -u EA -from 2020-08-30 -to 2020-09-15        Downloads all of @EA's
                                                          deleted Tweets *archived*
                                                          between August 30, 2020 to
                                                          September 15, 2020

## Installation
### For Windows only
 1. Download the latest EXE file.
 2. Launch Command Prompt in the EXE file's directory.
 3. Run the command `twayback_all -u USERNAME` (Replace `USERNAME` with your target handle).

### For Windows, Linux, and macOS
 1. Download the latest Python script ZIP file.
 2. Extract ZIP file to a directory of your choice.
 3. Open terminal in that directory.
 4. Run the command `pip install -r requirements.txt`.
 5. Run the command `twayback_all.py -u USERNAME` (Replace `USERNAME` with your target handle).
 

## Screenshots
**(I'm aware that screenshots for pre-2016 Tweets aren't working. I'm currently trying my best to fix it, but I've been running into errors. As soon as I fix it, I will ship a version that works for all Tweets. Thanks for your patience!)**

Screenshots are done using Playwright. To successfully take screenshots, please follow these steps:
 1. Open a terminal window.
 2. Run: `playwright install`.

## Troubleshooting
The larger the number of tweets your query has the higher your chances of encountering errors during execution. The default speed settings for `--semaphore-size` and `--batch-size` are set to the fastest possible execution. Reduce these numbers to slow down your execution and reduce the chance of errors. 

## Things to keep in mind
 - Quality of the HTML files depends on how the Wayback Machine saved them. Some are better than others.
 - This tool is best for text. You might have some luck with photos. You cannot download videos.
 - By definition, if an account is suspended or no longer exists, all their Tweets would be considered deleted.
 - Custom date range is not about when Tweets were made, but rather when they were _archived_. For example, a Tweet from 2011 may have been archived today.

## Call for help 🙏

