# Django Plus Forms

> Generic form creation through plugins.


**Quickstart**

`pip install git+https://github.com/InQuant/djangocms-plus-forms`

You also need to add
```python
INSTALLED_APPS = [
    ...
    'plusforms',
    'django.forms', # if not already included
    ...
]
```
to INSTALLED_APPS

### How to hook into submit (Example)
```python
from cms.plugin_pool import plugin_pool
from plusforms.cms_plugins import GenericFormPlugin as OldGenericFormPlugin
from plusforms.models import SubmittedForm

plugin_pool.unregister_plugin(OldGenericFormPlugin)


@plugin_pool.register_plugin
class GenericFormPlugin(OldGenericFormPlugin):
    def post_save(self, context, instance, obj: SubmittedForm = None):
        print('Hooked')
```


### Optional Setting
**PLUSFORMS_FIELDS**
> Define custom form fields
> (Default: None)
```python
PLUSFORMS_FIELDS = [
    'my_app.my_module.my_fields.CustomField',
]
```

**PLUSFORMS_MEDIA_UPLOAD**
> Custom destination folder for FileField uploads. (Default: 'media/plusform_uploads/')

```python
PLUSFORMS_MEDIA_UPLOAD = 'media/form_uploads/'
```

### ToDo
Add Date/DateTime form field with a good datetime picker.
 

### Known Bugs
Nothing yet