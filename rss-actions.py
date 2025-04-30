import requests, re
import os, os.path
from feedgen.feed import FeedGenerator
from urllib.request import urljoin
from bs4 import BeautifulSoup
import email.utils, dateutil

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
  fg.link(bs.find("link", rel='alternate').get_text())
  fg.link(bs.find("link", rel='self').get_text())
  fg.logo(bs.find("logo").get_text())
  fg.subtitle(bs.find("subtitle").get_text())

  for e in bs.find_all("entry"):
    fe = fg.add_entry()

    fe.updated(e.find("updated").get_text())

    fe.id(e.find("id").get_text())
    fe.title(e.find("title").get_text())
    fe.content(e.find("content").get_text(), type="xhtml")
    fe.summary(e.find("summary").get_text())
    fe.link(href=e.find("link").get("href"))
    fe.media.thumbnail(url=e.find("media:thumbnail").get("url"))
  return fg


def get_sitemap_bs(url, last_update=None):
  url = urljoin(url,'/sitemap.xml')

  head = requests.head(url)
  if 'last-modified' in head.headers and last_update and email.utils.parsedate_to_datetime(head.headers['last-modified']) < last_update:
    return BeautifulSoup('<sitemapindex></sitemapindex>', features="xml")
  return BeautifulSoup(requests.get(url).content, features="xml")

def the_dowsers_articles(last_update=None):
  return list(map(lambda x: x.string.strip(), get_sitemap_bs("https://the-dowsers.com", last_update).find_all("loc", string=re.compile(r'https://www.the-dowsers.com/the-dowser-posts/.*'))))

def the_dowsers_feed():
  global NUM_LATEST_FEEDS

  fg = None
  new_articles = None

  if os.path.exists("dist/the-dowsers_historical.atom"):
    fg = feed_from_atom("dist/the-dowsers_historical.atom")
    new_articles = filter(
      lambda url: url not in list(map(
        lambda e: e.id(),
        fg.entry()
      )),
      the_dowsers_articles(dateutil.parser.parse(fg.entry()[-1].find("updated").get_text()))
    )
  else:
    fg = FeedGenerator()
    fg.load_extension('media', atom=True, rss=True)

    fg.id('http://the-dowsers.com')
    fg.title('The Dowsers')
    fg.link( href='http://the-dowsers.com', rel='alternate' )
    fg.link( href='http://the-dowsers.com', rel='self' )
    fg.logo('https://cdn.prod.website-files.com/669681ffaf2044783667eeb1/669681ffaf2044783667eed8_the-dowsers-logo-p-500.png')
    fg.subtitle('A Magazine About Playlists')
    fg.language('en')

    new_articles = the_dowsers_articles()

  for i, url in enumerate(new_articles):
    print(f"Info: scraping article {i+1}/{len(new_articles)}: {url}")
    bs = BeautifulSoup(requests.get(url).content, 'html.parser')
    fe = fg.add_entry()

    blog_post = bs.find(class_="blog-posts-block")
    spotify_embed = bs.find(class_="spotify-embeded")

    fe.id(url)
    fe.title(bs.find("title").string.strip())
    fe.content(str(blog_post), type="xhtml")
    if spotify_embed:
      fe.content(fe.content()['content']+str(spotify_embed.find("iframe")), type="xhtml")
    fe.summary(blog_post.find(class_="paragraph").get_text().strip())
    fe.media.thumbnail(url=bs.find(class_="blog-image").get("src"))
    fe.link(href=url)

  
  fg.atom_file("dist/the-dowsers_historical.atom", pretty=True)
  fg_latest = feed_from_atom("dist/the-dowsers_historical.atom")

  for e in fg_latest.entry()[:-NUM_LATEST_FEEDS]:
    fg_latest.remove_entry(e)
  fg_latest.atom_file("dist/the-dowsers.atom", pretty=True)

the_dowsers_feed()