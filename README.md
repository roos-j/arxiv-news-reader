# ArXiv News Reader

This is a simple command-line tool to filter and display arXiv announcements according to preferred authors, keywords and categories.
 - Does *not* involve scraping of the arXiv website; relies only on arXiv's e-mail announcements.
 - ArXiv announcements fetched and parsed from user-provided  e-mail account.
 - Generates HTML reports sorted by favorite authors,keywords and categories in a similar style as displayed on the arXiv website

## Usage
  1. Set up an e-mail account and configure it to receive your selection of daily arXiv e-mail announcements. (It is recommended to create a dedicated e-mail account for this.)
   
  2. Enter IMAP server, username and password for the e-mail account in `config.ini`.
   
  3. Configure preferences:
     -  favorite authors in *keyauthors.txt*
     -  favorite keywords in *keywords.txt*
     -  favorite categories (such as math.CA, math.AP, etc.) in *keycategories.txt*

  4. To check arXiv news run 

          python arxivnewsreader.py

     A report will be generated from all new (unread) arXiv announcement e-mails. Processed e-mails are marked as read.

### Notes
- Currently the only supported method to connect with e-mail servers is IMAP/Basic Auth (username and password).
- Gmail and Microsoft stopped supporting Basic Auth in 2023.
- With many email providers still supporting Basic Auth it will be necessary to use an "app password".

## Settings 
Settings can be adjusted in `config.ini`:

  - `server`: IMAP e-mail server to fetch news from
  - `user`:  username on the IMAP e-mail server
  - `passwd`: if this is non-empty, it will be used as the password to login to the e-mail account
  - `include_remaining`: if this is `1`, items that do not match a favorite author, keyword or category will also be included in the report (by default they are discarded)
  - `verbose`: if this is `1`, the program will output some additional information on the progress
  - `outfile`: file name format of HTML report (using conventions from Python's `datetime.strftime`)
  - `open_outfile`: if this is `1`, then the finished report will be automatically opened in a browser
  - `keyauthors_file`: list of favorite authors will be read from this file (one author in each line)
  - `keywords_file`: list of favorite keywords will be read from this file (one keyword in each line)
  - `keycategories_file`: list of favorite categories will be read from this file (one category in each line)
  - `mailbox`: name of IMAP mailbox to read from
  - `subject`: string to search for in e-mail subject lines to detect arXiv announcement e-mails
 