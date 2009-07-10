from google.appengine.ext import db

from google.appengine.api.urlfetch import fetch, DownloadError
from helpers import render, view, host_for_url

from lib.BeautifulSoup import BeautifulSoup, HTMLParseError, UnicodeDammit
from logging import debug, info, warning, error

DEFAULT_TITLE = '[pagefeed saved item]'

import re

class Unparseable(ValueError):
	pass

def ascii(s):
	return s.decode('ascii', 'ignore')

class Replacement(object):
	def __init__(self, desc, regex, replacement):
		self.desc = desc
		self.regex = regex
		self.replacement = replacement
	
	def apply(self, content):
		return self.regex.sub(self.replacement, content)

def normalize_spaces(s):
	"""replace any sequence of whitespace
	characters with a single space"""
	return ' '.join(s.split())

# a bunch of regexes to hack around lousy html
dodgy_regexes = (
	Replacement('javascript',
		regex=re.compile('<script.*?</script[^>]*>', re.DOTALL | re.IGNORECASE),
		replacement=''),
	Replacement('double double-quoted attributes',
		regex=re.compile('(="[^"]+")"+'),
		replacement='\\1'),
	)

class Page(db.Model):
	url = db.URLProperty(required=True)
	content = db.TextProperty()
	title = db.StringProperty()
	error = db.TextProperty()
	owner = db.UserProperty(required=True)
	date = db.DateTimeProperty(auto_now_add=True)
	
	@staticmethod
	def _get_title(soup):
		title = unicode(getattr(soup.title, 'string', DEFAULT_TITLE))
		return normalize_spaces(title)
	
	@staticmethod
	def _get_body(soup):
		[ elem.extract() for elem in soup.findAll(['script', 'link', 'style']) ]
		return unicode(soup.body or soup)

	@staticmethod
	def _remove_crufty_html(content):
		for replacement in dodgy_regexes:
			content = replacement.apply(content)
		return content
	
	def populate_content(self, raw_content):
		self.error = None
		try:
			soup = self._parse_content(raw_content)
			self.content = self._get_body(soup)
			self.title = self._get_title(soup)
		except Unparseable, e:
			safe_content = ascii(raw_content)
			self._failed(str(e), safe_content)
	
	@classmethod
	def _parse_methods(cls):
		def unicode_cleansed(content):
			content = UnicodeDammit(content, isHTML=True).markup
			return BeautifulSoup(cls._remove_crufty_html(content))
		
		def ascii_cleansed(content):
			content = ascii(content)
			return BeautifulSoup(cls._remove_crufty_html(content))
		
		return (
			BeautifulSoup,
			unicode_cleansed,
			ascii_cleansed)
	
	@classmethod
	def _parse_content(cls, raw_content):
		first_err = None
		for parse_method in cls._parse_methods():
			try:
				return parse_method(raw_content)
			except HTMLParseError, e:
				if first_err is None:
					first_err = e
				error("parsing (with %s) failed: %s" % (parse_method, e))
				continue
		raise Unparseable(str(first_err))

	def fetch(self):
		try:
			response = fetch(self.url)
			if response.status_code >= 400:
				raise DownloadError("request returned status code %s\n%s" % (response.status_code, response.content))
			self.populate_content(response.content)
		except DownloadError, e:
			self._failed(str(e), 'no content was downloaded')
	
	def _failed(self, error, content):
		debug("error: %s" % (error,))
		self.title = DEFAULT_TITLE
		self.error = error
		self.content = content
	
	def update(self):
		if self.error is not None:
			info("page %s had an error - redownloading...." % (self.url,))
			self.fetch()
			self.save()
			if self.error is None:
				info("page %s retrieved successfully!" % (self.url,))
	
	def put(self, *a, **k):
		if self.content is None:
			self.fetch()
		super(type(self), self).put(*a,**k)

	@classmethod
	def find_all(cls, owner, limit=50):
		return db.Query(cls).filter('owner =', owner).order('-date').fetch(limit=limit)
	
	@classmethod
	def find(cls, owner, url):
		return db.Query(cls).filter('owner =', owner).filter('url =', url).get()
	
	def as_html(self):
		return render('page.html', {'page':self, 'error': self.error is not None})
	html = property(as_html)
	
	def _get_host(self):
		return host_for_url(self.url)
	host = property(_get_host)
	
	def _get_soup(self):
		if self.error:
			return None
		return BeautifulSoup(self.content)
	soup = property(_get_soup)
	
	def _get_base_href(self):
		base_parts = self.url.split('/')
		if len(base_parts) > 3: # more parts than ("http:", "", "server")
			base_parts = base_parts[:-1] # trim the last component
		base = '/'.join(base_parts) + '/'
		return base
	base_href = property(_get_base_href)

