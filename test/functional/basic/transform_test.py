from pagefeed.test.helpers import *
from models import transform, Transform
from google.appengine.api import users

from pagefeed.test import fixtures


class TransformAddTest(TestCase):
	path = "/transform/"
	default_opts = dict(host_match='localhost', selector='div[class=foo]', name="xform")
	
	def tearDown(self):
		[t.delete() for t in transform.Transform.all()]

	def fill_in_form(self, form, d):
		for k, v in d.items():
			form.set(k, v)

	def add(self, form=None, **kwargs):
		if form is None:
			form = self.get().forms['new_transform']
		self.fill_in_form(form, kwargs)
		self.assertEqual(form.method, 'POST')
		self.assertEqual(form.action, self.path)
		return form.submit()

	def get(self, **kwargs):
		return fixtures.app().get(self.path)

	def delete(self, form):
		self.assertEqual(form.method, 'POST')
		self.assertEqual(form.action, self.path + 'del/')
		return form.submit()

	def first_form(self, match, request):
		for form in request.forms.values():
			if form.id is not None and form.id.startswith(match):
				return form
		raise KeyError("no %r forms found in %r" % (match, [x.id for x in request.forms.values()]))

	def all_transforms(self):
		return transform.Transform.all().fetch(100)

	def test_should_add_a_transform_and_redirect_to_index(self):
		kw = dict(host_match='localhost', selector='div[class=foo]', name="xform")
		xform = mock('transform')
		create_params = kw.copy()
		create_params['owner'] = fixtures.a_user
		
		mock_on(transform.Transform).create.is_expected.with_('follow', **create_params).returning(xform.raw)
		response = self.add(**kw)
		self.assertEqual(response.follow().request.url, fixtures.app_root + 'transform/')

	@ignore("not yet implemented")
	def test_should_show_error_message_on_failure(self):
		form = self.get().forms['new_transform']
		response = form.submit(status=400)
		response.mustcontain("Error:")

	@ignore("broken because of import path messups in GAE")
	def test_should_delete_a_transform_and_redirect_to_index(self):
		response = self.add(**self.default_opts).follow()
		self.assertEqual(len(self.all_transforms()), 1)
		
		delete_form = self.first_form('delete', response)
		response = self.delete(delete_form)
		self.assertEqual(len(self.all_transforms()), 0)
		self.assertEqual(response.follow().request.url, fixtures.app_root + 'transform/')

	@ignore("broken because of import path messups in GAE")
	def test_should_update_an_existing_transform(self):
		page = self.add(**self.default_opts).follow()
		edit_form = self.first_form('edit', page)
		
		for k,v in self.default_opts.items():
			self.assertEqual(edit_form[k].value, v) #TODO: check webtest API

		all_xforms = self.all_transforms()
		self.assertEqual(len(all_xforms), 1)

		response = self.add(edit_form, name="the second name")
		updated_xforms = self.all_transforms()
		self.assertEqual(len(updated_xforms), 1)

		# selector, etc should stay the same:
		self.assertEqual(all_xforms[0].selector, updated_xforms[0].selector)

		# but names should be different:
		self.assertEqual(all_xforms[0].name, self.default_opts['name'])
		self.assertEqual(updated_xforms[0].name, 'the second name')
		
		self.assertEqual(response.follow().request.url, fixtures.app_root + 'transform/')

	def test_should_show_a_list_of_transforms(self):
		response = self.add(host_match='localhost', selector='div[class]', name="transform 1").follow()
		response.mustcontain("transform 1")
		response.mustcontain("div[class]")
		response.mustcontain("localhost")
		self.assertEqual(response.request.url, fixtures.app_root + 'transform/')



