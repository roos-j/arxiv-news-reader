ArXiv News Reader
(c) 2016, Joris Roos <roos.jor@gmail.com>
Python 3

v1.0
 
Features:
 - parse arXiv announcements as received from e-mail alerts into an internal format
 - keep a database of news items (called entries)
 - generate HTML reports
 - sort by preferred authors, keywords, categories
 - fetch arXiv e-mail alerts from a given IMAP inbox
 - read settings from a configuration file

Usage:
  1. Set up an e-mail account and configure it to receive your selection of daily arXiv e-mail announcements.
  2. List your favorite authors in 'keyauthors.txt', favorite keywords in 'keywords.txt', and favorite categories
       (such as math.CA, math.AP, etc.) in 'keycategories.txt'
  3. Run 'python arxivnewsreader.py' to check the news.
     The items from recent (unseen) e-mail announcement(s) will be filtered 
     according to your favorite authors, keywords and categories.

  Some additional settings are contained in 'config.ini'.
    outfile            -    file name format of HTML report (using conventions from Python's datetime.strftime)
    keyauthors_file    -    list of favorite authors will be read from this file (one author in each line)
    keywords_file      -    list of favorite keywords will be read from this file (one keyword in each line)
    keycategories_file -    list of favorite categories will be read from this file (one category in each line)
    open_outfile       -    if this is 1, then the finished report will be automatically opened in a browser
    mailbox            -    name of IMAP mailbox to read from
    include_remaining  -    if this is 1, items that do not match a favorite author, keyword or category will also be included in the report (by default they are discarded)
    subject            -    string to search for in e-mail subject lines to detect arXiv announcement e-mails
    verbose            -    if this is 1, the program will output some additional information on the progress
    server             -    IMAP e-mail server to fetch news from
    user               -    user name on the IMAP e-mail server
    passwd             -    if this is non-empty, it will be used as the password to login to the e-mail account
