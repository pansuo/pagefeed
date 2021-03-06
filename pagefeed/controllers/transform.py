import cgi
from google.appengine.ext import db

from base import *
from pagefeed.models import Transform

class TransformHandler(BaseHandler):
	root = "/transform/"

	def all_instances(self):
		return Transform.find_all(self.user())
	
	def get(self):
		transforms = self.all_instances().fetch(limit=50)
		self.response.out.write(render_page('transforms', {'transforms':transforms}))
	
	def key(self):
		key = self.request.get('key')
		if not key:
			key = None
		return key

	def _get_transform_params(self):
		params = dict(owner=self.user())
		for param in Transform.required_properties:
			if param in params: continue
			value = self.request.get(param)
			if not value:
				raise ValueError(param)
			params[param] = value
		return params

	def post(self):
		transform_params = self._get_transform_params()
		if self.key() is not None:
			xform = db.get(self.key())
			assert isinstance(xform, Transform)
			[setattr(xform, k, v) for k,v in transform_params.items()]
		else:
			xform = Transform.create(self.request.get('action'), **transform_params)
		xform.put()
		if self.is_ajax():
			self.response.out.write(render('snippets', 'transform.html', {'transform':xform}))
		else:
			self.redirect(self.root)

class TransformDeleteHandler(TransformHandler):
	def post(self):
		debug("key: %r" % (self.key(),))
		xform = Transform.get(self.key())
		xform.delete()
		if not self.is_ajax():
			self.redirect(self.root)

