import requests, re
import os, os.path
from feedgen.feed import FeedGenerator
from urllib.request import urljoin
from bs4 import BeautifulSoup
import email.utils
from more_itertools import flatten

os.system("mkdir dist")

NUM_LATEST_FEEDS = 30

''' DONE
- added thumbnails
- cleaner summary
- read already existing atom_file to avoid unnecessary scraping
- implement reading .atom file back into feedgen instead of caching, don't need duplicates
- find way to extract last 10-20 entries from feedgen (removing entries from a copy of historical)
- partition into historical.atom and "latest".atom
- check last-modified of sitmap.xml, check if post id (url) already an entry
- add spotify-embed if possible
'''

''' TODO
- multi-threaded? (might be overkill if site doesn't update much)
- separate "branches?" for each site
'''

def feed_from_atom(f):
  fg = FeedGenerator()
  fg.load_extension('media', atom=True, rss=True)

  bs = BeautifulSoup(open(f).read(), features="xml").find("feed")
  fg.updated(bs.find("updated").get_text())
  fg.id(bs.find("id").get_text())
  fg.title(bs.find("title").get_text())
  fg.link(href=bs.find("link", rel='alternate').get_text(), rel='alternate')
  fg.link(href=bs.find("link", rel='self').get_text(), rel='self')
  fg.logo(bs.find("logo").get_text())
  subtitle = bs.find("subtitle")
  if subtitle:
    fg.subtitle(subtitle.get_text())

  for e in reversed(bs.find_all("entry")):
    fe = fg.add_entry()

    fe.updated(e.find("updated").get_text())

    fe.id(e.find("id").get_text())
    fe.title(e.find("title").get_text())
    fe.content(e.find("content").get_text(), type="html")
    if e.find("summary"):
      fe.summary(e.find("summary").get_text())
    else:
      fe.summary("")
    fe.link(href=e.find("link").get("href"))
    thumbnail = e.find("media:thumbnail")
    if thumbnail:
      fe.media.thumbnail(url=thumbnail.get("url"))
  return fg


def get_sitemap_bs(url, last_update=None):
  print(f"({url}) Info: last update at {last_update}.")
  url = urljoin(url,'/sitemap.xml')
  
  headers = {}
  if last_update: headers["if-modified-since"] = email.utils.format_datetime(last_update)
  
  head = requests.head(url, headers=headers)
  if 'last-modified' in head.headers:
    last_modified = email.utils.parsedate_to_datetime(head.headers['last-modified'])
    print(f"({url}) Info: last modified at {last_modified}.")
    if last_update and last_modified < last_update:
      print("Info: No need to get sitemap")
      return BeautifulSoup('<sitemapindex></sitemapindex>', features="xml")
  return BeautifulSoup(requests.get(url).content, features="xml")

def get_articles(url, regexes, last_update=None):
  return list(flatten([list(map(lambda x: x.string.strip(), get_sitemap_bs(url, last_update).find_all("loc", string=regex))) for regex in regexes]))

def update_feed(url, feed_name, regexes, parse_func):
  global NUM_LATEST_FEEDS

  fg = None
  new_articles = None

  if os.path.exists(f"dist/{feed_name}_historical.atom"):
    fg = feed_from_atom(f"dist/{feed_name}_historical.atom")
    new_articles = list(filter(
      lambda url: url not in list(map(
        lambda e: e.id(),
        fg.entry()
      )),
      get_articles(url, regexes, fg.entry()[-1].updated())
    ))
  else:
    fg = FeedGenerator()
    fg.load_extension('media', atom=True, rss=True)

    homepage = BeautifulSoup(requests.get(url).content, 'html.parser')

    fg.id(url)
    fg.link(href=url, rel='alternate')
    fg.link(href=url, rel='self')
    fg.logo(homepage.find('link', rel='icon').get('href'))
    fg.title(homepage.find('title').get_text())
    #fg.subtitle('A Magazine About Playlists')
    fg.language('en')

    new_articles = get_articles(url, regexes)

  print(f"({url}) Info: {len(new_articles)} new articles.")

  for i, url in enumerate(new_articles):
    print(f"({url}) Info: scraping article {i+1}/{len(new_articles)}: {url}")
    bs = BeautifulSoup(requests.get(url).content, 'html.parser')
    fe = fg.add_entry()

    try:
      parse_func(url, bs, fe)
    except:
      print("Error parsing:", url)
  
  fg.atom_file(f"dist/{feed_name}_historical.atom", pretty=True)
  fg_latest = feed_from_atom(f"dist/{feed_name}_historical.atom")

  for e in fg_latest.entry()[:-NUM_LATEST_FEEDS]:
    fg_latest.remove_entry(e)
  fg_latest.atom_file(f"dist/{feed_name}.atom", pretty=True)

def dowser_extract(url, bs, fe):
  blog_post = bs.find(class_="blog-posts-block")
  spotify_embed = bs.find(class_="spotify-embeded")

  fe.id(url)
  fe.title(bs.find("title").string.strip())
  fe.content(str(blog_post), type="html")
  if spotify_embed:
    fe.content("<div>"+fe.content()['content']+str(spotify_embed.find("iframe"))+"</div>", type="html")
  fe.summary(blog_post.find(class_="paragraph").get_text())
  fe.media.thumbnail(url=bs.find(class_="blog-image").get("src"))
  fe.link(href=url)


def default_extract(url, bs, fe):
  fe.id(url)
  fe.title(bs.find("title").string.strip())
  fe.content(str(bs.find("main")), type="html")
  fe.summary(bs.find("p").get_text())
  img = bs.find("img")
  if img:
    fe.media.thumbnail(url=img.get("src"))
  fe.link(href=url)

def dazeland_extract(url, bs, fe):
  fe.id(url)
  fe.link(href=url)
  fe.title(bs.find("title").string.strip())
  fe.content(str(bs.find(style="width: 844px")), type="html")
  fe.summary(bs.find("p").get_text())
  img = bs.find("img")
  if img:
    fe.media.thumbnail(url=img.get("src"))

update_feed('https://dazeland.com', 'dazeland', [re.compile(r'https://www.dazeland.com/.+')], dazeland_extract)
update_feed('https://the-dowsers.com', 'the-dowsers', [re.compile(r'https://www.the-dowsers.com/the-dowser-posts/.*')], dowser_extract)
update_feed('https://gwennseemel.com', 'gwenn-seemel', [re.compile(r'https://gwennseemel.com/.*')], default_extract)
