#!/usr/bin/python3
# (c) 2016-2017 Joris Roos <roos.jor@gmail.com>
# MIT License

''' ArxivNewsReader '''

import re
import datetime
import sys
#import pickle
import string
import urllib.parse
import unicodedata
import codecs
import webbrowser
import os
import configparser
import quopri

import imaplib
import getpass
import email

__version__ = "0.0.1"

class Entry:
    '''Represents a single article announcement (could be a revision).'''

    def __init__(self, text, verbose=False):
        self._parse(text)
        self._validate(verbose=verbose)

    def _validate(self, verbose=False):
        self._valid = False
        if "authors" not in self._data:
            if verbose:
                print("Invalid entry '%s': no author information found."%str(self._data)[:50])
            return
        authors_raw = self._data["authors"] # tex_to_html.tex_to_html(self._data["authors"])
        # originally: re.sub(r"[^\w\-\.\s]","",a,flags=re.UNICODE)
        auth = [re.sub(r"[^\w\-\.\s]","",a.strip(),flags=re.UNICODE)
            for a in re.split(",|and ", re.sub(r"\([^\)]*\)","", authors_raw,
                                flags=re.UNICODE),flags=re.UNICODE) if len(a.strip())]
        if len(auth) == 0:
            if verbose:
                print("Invalid entry '%s': empty author list."%str(self._data)[:50])
            return
        self._auth = auth
        if "arxiv" in self._data:
            self._id = self._data["arxiv"]
        else:
            if verbose:
                print("Invalid entry '%s': no arXiv id found."%str(self._data)[:50])
            return
        if "date" in self._data:
            raw = self._data["date"]
            m = re.search(r"\(([\w,]*)\)", raw)
            if m: 
                self._data["size"] = m.group(1)
            raw = re.sub(r"\([\w,]*\)", "", raw).strip()
            self._data["date"] = raw
            try:
                self._t = datetime.datetime.strptime(raw, "%a, %d %b %Y %H:%M:%S %Z")
            except ValueError:
                print("Invalid entry '%s': no date found."%str(self._data)[:50])
                return
        self._valid = True

    def __str__(self):
        if not self._valid:
            return "(invalid entry)"
        return ", ".join(self._auth) + ". %s. arXiv:%s"%(self._data["title"],self._id) + \
                (" (revised version)" if self._is_revision else "") + " (%s)"%str(self._t)

    def _parse(self, text):
        entry = {}
        lines = text.split("\n")
        mode = 0
        extra = ""
        self._is_revision = False
        for l in lines:
            if mode == 2:
                # Abstract
                if l.strip().startswith("\\\\"):
                    entry[key] = val
                    mode = -1
                    break
                val += (" " if len(val)>0 else "") + l.strip()
            if mode == 1:
                # Multiline
                if not ":" in l and not l.startswith("\\\\"):
                    val += " " + l.strip()
                else:
                    entry[key] = val
                    mode = 0
            if mode == 0:
                if l.startswith(REV_PREFIX):
                    l = l[len(REV_PREFIX):].strip()
                    entry["date"] = l
                    self._is_revision = True
                if ":" in l:
                    # Entry description data
                    parts = l.split(":",1)
                    key = parts[0].strip().lower()
                    val = parts[1].strip()
                    mode = 1
                elif l.strip() == "\\\\":
                    mode = 2
                    key = "abstract"
                    val = ""
        if mode > 0:
            entry[key] = val
        extra = extra.strip()
        if len(extra) > 0:
            entry["extra"] = extra
        if "arxiv" in entry:
            entry["arxiv"] = entry["arxiv"].split(" ")[0]
        self._data = entry

    def is_valid(self):
        return self._valid

    def is_revision(self):
        return self._is_revision

    def get_id(self):
        return self._id

    def get_date(self):
        return self._t

    def __hash__(self):
        return hash((self._t, self._id))

    def __eq__(self, o):
        return isinstance(o, Entry) and self._t == o._t and self._id == o._id

    def __lt__(self, o):
        return self._t.__lt__(o._t)
    def __le__(self, o):
        return self._t.__le__(o._t)
    def __gt__(self, o):
        return self._t.__gt__(o._t)
    def __ge__(self, o):
        return self._t.__ge__(o._t)

    def get_data(self):
        return self._data

    def get_authors(self):
        return self._auth

    def get_content(self, key):
        if key in self._data: return self._data[key]
        else: return ""

    def get_title(self):
        return self.get_content("title")

    def get_abstract(self):
        return self.get_content("abstract")

    def get_categories(self):
        return self.get_content("categories")

REV_PREFIX = "replaced with revised version"

# def load(file="arxiv.db", verbose=False):
#     with open(file, "rb") as f:
#         db = pickle.load()
#         if verbose:
#             print("Database loaded from '%s'."%file)
#     return db

# def dump(file="arxiv.db", verbose=False):
#     with open("arxiv.db", "wb") as f:
#         pickle.dump(db, f)
#         f.close()
#         if verbose: print("Database written to '%s'."%file)
#         return True
def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn')

def parse_announcement(text, db=None, verbose=False):
    '''Parse all the entries given in text and return a 2-tuple, 
       the first object being a dict object with keys being
       the arXiv ids and values sets of Entry objects each corresponding to one separate revision,
       and the second object a list of the parsed entries (not checked for doubles).'''
    if db is None:
        db = {}
    entries_raw = re.split(r"-[-\r\n]*\s*\n\\\\\s*\n", text)[1:]

    new_c = 0
    rev_c = 0
    total_c = len(entries_raw)
    invalid_c = 0
    rep_c = 0
    entry_set = set()
    for e in entries_raw:
        entry = Entry(e,verbose=verbose)
        if not entry.is_valid():
            invalid_c += 1
            continue
        entry_set.add(entry)
        aid = entry.get_id()
        if aid in db:
            if entry in db[aid]:
                rep_c += 1
                continue
            db[aid].add(entry)
        else:
            db[aid] = {entry}
        if entry.is_revision():
            rev_c += 1
        else:
            new_c += 1
        #print("* %s"%str(entry)[:50])
    if verbose:
        print("%d entries total, %d new, %d revisions (%d invalid, %d repeated)"%(total_c,new_c,rev_c, invalid_c, rep_c))
    entries = list(entry_set)
    entries.sort()
    return (db,entries[::-1])

def generate_html_report(entries, keyauthors, keywords, keycategories, include_remaining=True, verbose=False):
    '''Return HTML code for a report on the Entry objects contained in entries.

        keyauthors - entries that are authored by one of the authors in this list are reported in the first section,
        keywords - remaining entries whose title or abstract contains one of these keywords are reported in the next section,
        keycategories - remaining entries whose category matches one of these are reported in the next section,
        include_remaining - if this is True, the remaining entries form another section.
    '''
    matches_auth = []
    matches_keyw = []
    matches_cat = []
    remaining = []
    prep = lambda s: "".join([c for c in strip_accents(s.lower()) if c in "abcdefghijklmnopqrstuvwxyz0123456789"]).strip()
    min_date = datetime.datetime.now()
    max_date = datetime.datetime(1,1,1)
    for e in entries:
        if not e.is_valid():
            if verbose:
                print("Ignoring invalid entry.")
            continue
        content = prep(e.get_title() + " " + e.get_abstract())
        cats = prep(e.get_categories())
        accepted = False
        if any(any(match_names(m,n) for m in keyauthors) for n in e.get_authors()):
            matches_auth.append(e)
            accepted = True
        elif any(re.search(prep(k), content) for k in keywords):
            matches_keyw.append(e)
            accepted = True
        elif any(re.search(prep(c), cats) for c in keycategories):
            matches_cat.append(e)
            accepted = True
        else:
            remaining.append(e)
        if accepted or include_remaining:
            if e.get_date() < min_date:
                min_date = e.get_date()
            if e.get_date() > max_date:
                max_date = e.get_date()

    if verbose:
        print("Sorted %d entries: %d author match, %d keyword match, %d category match, %d remaining"%(len(entries),len(matches_auth),len(matches_keyw),len(matches_cat),len(remaining)))

    s = '<?xml version="1.0" encoding="UTF-8"?>\n'
    s += '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"' + \
          '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
    s += '<html xmlns="http://www.w3.org/1999/xhtml" lang="en">\n<head>\n'
    days = (max_date-min_date).days
    if days <= 1:
        date_range = max_date.strftime("%b %d, %Y")
    elif days < 365:
        date_range = min_date.strftime("%b %d") + " to " + max_date.strftime("%b %d, %Y")
    else: 
        date_range = min_date.strftime("%b %d, %Y") + " to " + max_date.strftime("%b %d, %Y")
    s += '<title>ArXiv news report - %s</title>\n'%date_range
    s += '<link rel="stylesheet" type="text/css" media="screen" href="http://www.arxiv.org/css/arXiv.css?v=20161221" />\n'
    s += '''<script type="text/x-mathjax-config">
  MathJax.Hub.Config({tex2jax: {inlineMath: [['$','$']]}});
</script>
<script type="text/javascript" async
  src="https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS_CHTML">
</script>\n'''
    s += '</head>\n<body><div id="content"><div id="dlpage">\n'
    s += '<h1>ArXiv news report - %s</h1>\n'%date_range

    def gen_count(entries):
        rev_c = len([1 for e in entries if e.is_revision()])
        new_c = len(entries)-rev_c
        if len(entries):
            rv = "total of %d entries (%d new, %d revisions)"%(len(entries), new_c, rev_c)
        else: 
            rv = "no entries"
        return rv

    all_matches = matches_auth + matches_keyw + matches_cat
    if include_remaining: all_matches += remaining
    s += '<small>[ %s ]</small><br/>\n'%gen_count(all_matches) 

    section_templ = '<h3>%s</h3>\n<small>[ %s ]</small><br/>\n<dl>\n'
    def gen_section(caption, entries):
        rv = ""
        rv += section_templ%(caption, gen_count(entries))
        cnt = 0
        for b in [False,True]:
            for e in entries:
                if b == e.is_revision():
                    cnt += 1
                    rv += generate_html_entry_report(e,cnt)
        rv += '</dl>\n'
        return rv

    s += gen_section("Author matches", matches_auth)
    s += gen_section("Keyword matches", matches_keyw)
    s += gen_section("Category matches", matches_cat)
    if include_remaining:
        s += gen_section("Remaining", remaining)

    s += '</div></div></body>\n</html>\n'
    return s

def get_first_name(s):
    return s.split(" ")[0].replace(".","")

def get_last_name(s):
    return s.split(" ")[-1].replace(".","")

escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
    }

def escape(s):
    return "".join(escape_table.get(c,c) for c in s)

def generate_html_entry_report(entry, nr=1):
    '''Generate HTML report on single entry.'''
    t = string.Template('''
<dt>[$nr]&nbsp; <span class="list-identifier"><a href="http://www.arxiv.org/abs/$id" title="Abstract">arXiv:$id</a> [<a href="http://www.arxiv.org/pdf/$id" title="Download PDF">pdf</a>, <a href="http://www.arxiv.org/format/$id" title="Other formats">other</a>] $rev</span></dt>
<dd>
<div class="meta">
<div class="list-title mathjax">
<span class="descriptor">Title:</span>$title</div>
<div class="list-authors">
<span class="descriptor">Authors:</span> $authors
</div>
$comments
<div class="list-subjects">
<span class="descriptor">Categories:</span> $categories
</div>
<small>$date</small><br/>
<p class="mathjax">$abstract
</p>
</div>
</dd>
''')
    d = {}
    d["nr"] = str(nr)
    d["id"] = escape(entry.get_id())
    d["title"] = escape(entry.get_title())
    d["categories"] = escape(entry.get_categories())
    d["date"] = escape(entry.get_content("date"))
    comments = entry.get_content("comments")
    if len(comments):
        d["comments"] = '''
<div class="list-comments">
<span class="descriptor">Comments:</span> %s
</div>
        '''%escape(comments)
    else: d["comments"] = ""
    quote = urllib.parse.quote
    d["authors"] = ", ".join(['<a href="http://www.arxiv.org/find/all/1/au:+%s_%s/0/1/0/all/0/1">%s</a>'%
                        (quote(get_last_name(a)), quote(get_first_name(a)), escape(a)) for a in entry.get_authors()])
    d["abstract"] = escape(entry.get_abstract())
    d["rev"] = "(revision)" if entry.is_revision() else ""
    return t.substitute(d)
 
def match_names(mask,name):
    '''Check whether mask matches name (tolerate initials and missing name components).'''
    prep = lambda s: re.sub(r"[^\w\.\-]", "", s.lower(), flags=re.UNICODE).strip()
    mask = prep(mask)
    name = prep(name)
    mask = mask.replace(".", r"[\w\.\-]+\s?").replace(" ", r"\s[\w\.\-]*?\s?")
    return re.match(mask, name, re.UNICODE) is not None

FAILED = "fail"

def fetch_mail(server, user, passwd=None, subject="math daily", mailbox="INBOX", verbose=False):
    '''Fetch announcement mails from an IMAP server and return the concatenated announcements as string.
        - if passwd is None, the user will be prompted to enter a password
        - all e-mails containing subject (treated as regular expression) will be considered arXiv announcements
        - will look in the specified mailbox
    '''
    try:
        m = imaplib.IMAP4_SSL(server)
    except ConnectionRefusedError:
        print("Failed to connect to '%s' (connection refused)."%server)
        return FAILED
    except imaplib.IMAP4.error:
        print("Failed to connect to '%s'."%server)
        return FAILED
    except Exception as e:
        print("Error when connecting to '%s': %s"%(server,str(e)))
        return FAILED

    try:
        if not passwd:
            passwd = getpass.getpass()
        m.login(user, passwd)
    except imaplib.IMAP4.error as e:
        #print("Failed to login to '%s' (invalid username or password?)."%server)
        print(f"error logging in to {server}: {e}")
        return FAILED

    if verbose:
        print("Connected to '%s' as '%s'."%(server, user))

    rv,data = m.select(mailbox)
    if rv != 'OK':
        print("Failed to select mailbox '%s'."%mailbox)
        return ""
    rv,data = m.search(None, "ALL", "(UNSEEN)")
    if rv != 'OK':
        print("No messages found.")
        return ""

    msg_ids = data[0].split()
    content = ""
    cnt = 0
    for mid in msg_ids:
        rv, data = m.fetch(mid, '(RFC822)')
        if rv != 'OK':
            print("Error fetching message %s."%mid)
            continue
        msg = email.message_from_string(data[0][1].decode('UTF-8'))
        if re.search(subject.lower(), msg["Subject"].lower()):
            if msg.is_multipart():
                for payload in msg.get_payload():
                    if payload.get_content_type() != "text/plain":
                        continue
                    temp = quopri.decodestring(payload.get_payload()).decode("utf-8")
                    content += temp
            else:
                content += msg.get_payload(decode="base64").decode("UTF-8") + "\n"
            cnt += 1

    #for mid in msg_ids:
    #    m.store(mid, '-FLAGS', '\Seen')

    content = content.replace("\r\n", "\n")
    m.close()
    m.logout()

    if verbose and cnt > 0:
        print("Found %d message(s)."%cnt)

    return content

def load_lines_from_file(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            rv = f.readlines()
        return rv
    except IOError:
        print("Could not read from file '%s'."%file)
        return ""

def fetch_and_report(server, user, passwd=None, **args):
    verbose = args["verbose"] == "1"
    content = fetch_mail(server, user, passwd, subject=args["subject"],
                        mailbox=args["mailbox"], verbose=verbose)
    if content == FAILED:
        return
    if len(content) == 0:
        if verbose:
            print("No new announcements found.")
        return

    keyauthors = load_lines_from_file(args["keyauthors_file"])
    keywords = load_lines_from_file(args["keywords_file"])
    keycategories = load_lines_from_file(args["keycategories_file"])

    res = parse_announcement(content, dict(), verbose=verbose=="1")
    entries = res[1]
    report = generate_html_report(entries, keyauthors=keyauthors, keywords=keywords,
        keycategories=keycategories, include_remaining=args["include_remaining"]=="1",
        verbose=verbose)

    try:
        outf = datetime.datetime.today().strftime(args["outfile"])
        with codecs.open(outf, "w") as f:
            f.write(report)

        if args["open_outfile"] == "1":
            webbrowser.open("file://" + os.path.join(os.getcwd(), outf))
    except IOError as e:
        print("Couldn't access file: %s"%str(e))
    # except Exception as e:
    #     print("Unexpected error: %s"%str(e))

CONFIG_FILE = "config.ini"
USER_INPUT = "user input"

CONFIG_DEFAULTS = {
    "server": USER_INPUT,
    "user": USER_INPUT,
    "passwd": "",
    "subject": "math daily",
    "mailbox": "INBOX",
    "outfile": r"Report%Y-%m-%d_%H%M%S.html",
    "keywords_file": "keywords.txt",
    "keyauthors_file": "keyauthors.txt",
    "keycategories_file": "keycategories.txt",
    "include_remaining": "0",
    "open_outfile": "1",
    "verbose": "1"
}

def read_config_from_file():
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = CONFIG_FILE

    cfg = {}
    try:
        config = configparser.ConfigParser(interpolation=None)
        config.read(config_file)
        if "Config" in config:
            cfg = config["Config"]
        # else:
            #print("Error: missing/invalid config file.")
    except IOError:
        print("Error: couldn't read from '%s'."%config_file)

    write_cfg = False
    for cfg_key, default_val in CONFIG_DEFAULTS.items():
        if cfg_key not in cfg:
            if default_val == USER_INPUT:
                default_val = input("Enter %s: "%cfg_key)
            cfg[cfg_key] = default_val
            write_cfg = True

    if write_cfg:
        config = configparser.ConfigParser(interpolation=None)
        config["Config"] = cfg
        with open(config_file, "w", encoding="utf-8") as f:
            config.write(f)
        print("Wrote settings to config file '%s'."%config_file)
    return cfg

def main():
    print("ArXivNewsReader v" + __version__)
    cfg = read_config_from_file()
    fetch_and_report(**cfg)

if __name__ == "__main__":
    main()
