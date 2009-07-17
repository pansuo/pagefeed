import cgi

from base import *
from models import Transform

class TransformHandler(BaseHandler):
	root = "/transform/"
	def get(self):
		transforms = Transform.find_all(self.user())
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
			xform = Transform.get(self.key())
			[setattr(xform, k, v) for k,v in transform_params.items()]
		else:
			xform = Transform(**transform_params)
		xform.put()
		if self.is_ajax():
			self.response.out.write(render('snippets', 'transform.html', {'transform':xform}))
		else:
			self.redirect(self.root)

class TransformDeleteHandler(TransformHandler):
	def post(self):
		Transform.get(self.key()).delete()
