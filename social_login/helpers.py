class SimpleLocalProxy:
	def __init__(self, obj):
		self._obj = obj

	def __getattr__(self, name):
		return getattr(self._obj, name)

	def __setattr__(self, name, value):
		if name == '_obj':
			super().__setattr__('_obj', value)
		else:
			setattr(self._obj, name, value)
