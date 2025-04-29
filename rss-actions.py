import requests, re
from feedgen.feed import FeedGenerator
from urllib.request import urljoin
from bs4 import BeautifulSoup


''' TODO
- cache sitemap data, check last-modified
'''

def get_sitemap_bs(url):
  return BeautifulSoup(requests.get(urljoin(url,'/sitemap.xml')).content, features="xml")

def the_dowsers_articles():
  return list(map(lambda x: x.string.strip(), get_sitemap_bs("https://the-dowsers.com").find_all("loc", string=re.compile(r'https://www.the-dowsers.com/the-dowser-posts/.*'))))

def the_dowsers_feed():
  fg = FeedGenerator()
  fg.id('http://lernfunk.de/media/654321')
  fg.title('The Dowsers')
  fg.link( href='http://the-dowsers.com', rel='alternate' )
  fg.logo('https://cdn.prod.website-files.com/669681ffaf2044783667eeb1/669681ffaf2044783667eed8_the-dowsers-logo-p-500.png')
  fg.subtitle('A Magazine About Playlists')
  fg.link( href='http://the-dowsers.com', rel='self' )
  fg.language('en')

  articles = the_dowsers_articles()
  for i, url in enumerate(articles):
    console.log(f"Info: scraping article {i+1}/{len(articles)}: {url}")
    bs = BeautifulSoup(requests.get(url).content, 'html.parser')
    fe = fg.add_entry()

    blog_post = bs.find(class_="blog-posts-block")

    fe.id(url)
    fe.title(bs.find("title").string.strip())
    fe.content(str(blog_post), type="CDATA")
    fe.summary(blog_post.get_text().strip())
    fe.link(href=url)

  fg.atom_file("dist/the-dowsers.atom", True)

the_dowsers_feed()