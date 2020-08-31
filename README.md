# Django Plus Forms

> Generic form creation through plugins.


**Quickstart**

`pip install git+https://github.com/InQuant/djangocms-plus-forms`

You also need to add
```
INSTALLED_APPS = [
    ...
    'plusforms',
    'django.forms', # if not already included
    ...
]
```
to INSTALLED_APPS


### Optional Setting
**PLUSFORMS_FIELDS**
> Define custom form fields
> (Default: None)
```
PLUSFORMS_FIELDS = [
    'my_app.my_module.my_fields.CustomField',
]
```

**PLUSFORMS_MEDIA_UPLOAD**
> Custom destination folder for FileField uploads. (Default: 'media/plusform_uploads/')

```
PLUSFORMS_MEDIA_UPLOAD = 'media/form_uploads/'
```

### ToDo
Add Date/DateTime form field with a good datetime picker.
 

### Known Bugs
Nothing yet