import abc

from cms.plugin_pool import plugin_pool
from cmsplus.models import PlusPlugin
from cmsplus.plugin_base import PlusPluginBase, PlusPluginFormBase
from django import forms
from django.conf import settings
from django.core.validators import get_available_image_extensions
from django.utils.translation import ugettext_lazy as _

from plusforms.models import SubmittedForm
from plusforms.form_fields import get_available_form_fields, get_class
from plusforms.forms import PlusFormBase

import logging
logger = logging.getLogger('plusforms')

EXT_IMG_CHOICES = getattr(settings, 'PLUSFORMS_EXTENSIONS_IMAGE',
                          tuple((ext, ext) for ext in get_available_image_extensions()))

EXT_CHOICES = getattr(settings, 'PLUSFORMS_EXTENSIONS', (
    # text
    ('doc', 'doc'),
    ('docx', 'docx'),
    ('odt', 'odt'),
    # ('pdf', 'pdf'),
    ('rtf', 'rtf'),
    ('txt', 'txt'),

    # video
    ('avi', 'avi'),
    ('flv', 'flv'),
    ('dh264oc', 'ddh264ococ'),
    ('m4v', 'm4v'),
    ('mov', 'mov'),
    ('mp4', 'mp4'),
    ('mpg', 'mpg'),
    ('mpeg', 'mpeg'),
    ('wmv', 'wmv'),
    ('vob', 'vob'),
    ('swf', 'swf'),
    ('rm', 'rm'),

    # spreadsheet
    ('ods', 'ods'),
    ('xls', 'xls'),
    ('xlsx', 'xlsx'),
    ('xlsm', 'xlsm'),

    # presentation
    ('key', 'key'),
    ('odp', 'odp'),
    ('pps', 'pps'),
    ('ppt', 'ppt'),
    ('pptx', 'pptx'),

    # compressed
    ('7z', '7z'),
    ('rar', 'rar'),
    ('tar.gz', 'tar.gz'),
    ('zip', 'zip'),
    ('z', 'z'),

    # audio
    ('aif', 'aif'),
    ('mp3', 'mp3'),
    ('mpa', 'mpa'),
    ('ogg', 'ogg'),
    ('wav', 'wav'),
    ('wma', 'wma'),
    ('wpl', 'wpl'),

)) + EXT_IMG_CHOICES

EXT_CHOICES = sorted(EXT_CHOICES, key=lambda i: i[0])


class GenericFormPluginForm(PlusPluginFormBase):
    form_id = forms.SlugField(label=_('Form identifier'), required=True)

    success_text = forms.CharField(label=_('Success text'), widget=forms.Textarea)
    button_text = forms.CharField(label=_('Submit button text'), required=True, initial=_('Submit'))

    name = forms.CharField(label=_('Name'), required=False)
    description = forms.CharField(label=_('Description'), required=False, widget=forms.Textarea)


def snake_to_camel(s):
    """ huhu_foo_bar -> HuhuFooBar
    """
    return ''.join(x.capitalize() for x in s.split('_'))


@plugin_pool.register_plugin
class GenericFormPlugin(PlusPluginBase):
    cache = False
    form = GenericFormPluginForm
    name = _('Form')
    module = 'form'
    allow_children = True
    render_template = 'plusforms/base_form.html'

    @staticmethod
    def field_plugins(instance: PlusPlugin):
        children = []
        for child in instance.get_children() or []:
            if issubclass(child.get_plugin_class(), GenericFieldPlugin):
                children.append(child)
        return children

    @abc.abstractmethod
    def post_save(self, request, context, instance, obj: SubmittedForm = None):
        """
        Hook to customize what to do after object creation.
        """
        return context

    def get_user_form_class(self, context, instance):
        if not getattr(self, 'user_form_class', None):
            self.user_form_class = self.user_form_factory(context, instance)
        return self.user_form_class

    def get_user_form_fields(self, context, instance):
        fields = {}
        for child in self.field_plugins(instance):
            ci, cc = child.get_plugin_instance()
            fields[ci.glossary['field_id']] = cc.get_form_field(context, ci)
        return fields

    def user_form_factory(self, context, instance, module=__name__):
        fields = self.get_user_form_fields(context, instance)
        cls_name = snake_to_camel('%s_form' % instance.glossary.get('form_id').replace('-', '_'))
        attrs = dict(**fields, __module__=module)
        return type(cls_name, (PlusFormBase,), attrs)

    @classmethod
    def get_identifier(cls, instance):
        return "%s" % (
            instance.glossary.get('name'),
        )

    def render(self, context, instance, placeholder):
        request = context.get('request')
        user_form_cls = self.get_user_form_class(context, instance)

        sf = context.get('plus_form')
        if request.POST and request.POST.get('form-%s' % instance.id):
            name = sf.name if sf else self.get_identifier(instance)
            self.user_form = user_form_cls(request.POST, request.FILES, name=name, request=request, instance=sf)

            # validate and save
            if self.user_form.is_valid():
                try:
                    obj = self.user_form.save()
                    context['plus_form'] = obj
                    self.post_save(request, context, instance, obj)
                except Exception as e:
                    logger.error(str(e))
        else:
            # init for get
            self.user_form = user_form_cls(instance=sf)

        context['user_form'] = self.user_form
        return super(GenericFormPlugin, self).render(context, instance, placeholder)


class FormFieldPluginForm(PlusPluginFormBase):
    field_type = forms.ChoiceField()
    field_id = forms.SlugField(
        label=_('Identifier'),
        help_text=_('This will be the id and name attribute of this input. Needs to be unique inside a form!'),
        required=True
    )

    required = forms.BooleanField(label=_('Required'), initial=False, required=False)

    label = forms.CharField(label=_('Label'), required=False)
    help_text = forms.CharField(label=_('Help text'), required=False)
    field_placeholder = forms.CharField(label=_('Placeholder'), required=False)

    # if file or image
    max_mb = forms.IntegerField(required=False)
    allowed_extensions = forms.MultipleChoiceField(required=False, choices=EXT_CHOICES)

    min_px_width = forms.IntegerField(required=False)
    min_px_height = forms.IntegerField(required=False)

    @staticmethod
    def get_field_type_choices():
        r = []
        for FIELD_CLASS in get_available_form_fields():
            choice = [FIELD_CLASS.__name__, getattr(FIELD_CLASS, 'name', FIELD_CLASS.__name__)]
            r.append(choice)
        return r

    def __init__(self, *args, **kwargs):
        super(FormFieldPluginForm, self).__init__(*args, **kwargs)
        # set field choices
        self.fields['field_type'] = forms.ChoiceField(choices=self.get_field_type_choices)


@plugin_pool.register_plugin
class GenericFieldPlugin(PlusPluginBase):
    module = 'form'
    cache = False
    name = _('Field')
    allow_children = True
    form = FormFieldPluginForm
    fieldsets = (
        (None, {
            'fields': (
                'field_type',
                'field_id',
                'required',
                'label',
                'help_text',
                'field_placeholder',
            )
        }),
        (_('FileInput Options'), {
            'classes': ('file_input--wrapper',),
            'fields': ('max_mb', 'allowed_extensions', ),
        }),
        (_('ImageInput Options'), {
            'classes': ('image_input--wrapper',),
            'fields': ('min_px_width', 'min_px_height'),
        }),
    )

    class Media:
        js = ['plusform/admin/js/field.js']

    @staticmethod
    def get_field_class(instance):
        cls_name = instance.glossary.get('field_type')
        if not cls_name:
            raise ValueError('field_type not set')

        CLS = get_class(cls_name)
        if not CLS:
            raise AttributeError('"%s" does not exist' % cls_name)
        return CLS

    def get_render_template(self, context, instance, placeholder):
        CLS = self.get_field_class(instance)
        return CLS.template_name

    @classmethod
    def get_identifier(cls, instance):
        return "%s %s".strip() % (
            instance.glossary.get('field_type'),
            instance.glossary.get('label')
        )

    @classmethod
    def get_form_field(cls, context, instance):
        FIELD_CLASS = cls.get_field_class(instance)
        data = instance.glossary
        field_id = data.get('field_id', None)

        _attrs = {
            'placeholder': data.get('field_placeholder', ''),
            'id': field_id,
            'class': getattr(FIELD_CLASS, 'widget_class', ''),
        }
        input_type = getattr(FIELD_CLASS.widget, 'input_type', '')

        widget = FIELD_CLASS.widget(attrs=_attrs)
        widget.name = field_id
        widget.type = input_type

        field_kwargs = {
            'label': data.get('label', ''),
            'help_text': data.get('help_text', data.get('value', '')),
            'widget': widget,
            'required': data.get('required', False),
        }

        help_text = []

        max_mb = instance.glossary.get('max_mb')
        if max_mb:
            field_kwargs['max_mb'] = max_mb
            help_text.append(
                "Max. %s MB." % max_mb
            )

        min_w = instance.glossary.get('min_px_width')
        if min_w:
            field_kwargs['min_px_width'] = min_w

        min_h = instance.glossary.get('min_px_height')
        if min_h:
            field_kwargs['min_px_height'] = min_h

        if min_w or min_h:
            help_text.append('Minimum %s x %s. ' % (
                "*" if not min_w else "%spx" % min_w,
                "*" if not min_h else "%spx" % min_h,
            ))

        allowed_extensions = instance.glossary.get('allowed_extensions')
        if allowed_extensions:
            field_kwargs['allowed_extensions'] = allowed_extensions
            help_text.append("(%s) " % ", ".join(allowed_extensions))

        field_kwargs['help_text'] += " ".join(help_text)

        return FIELD_CLASS(**field_kwargs)

    @staticmethod
    def add_error_class(field):
        ele_classes = field.widget.attrs.get('class', '').split(' ')
        if 'is-invalid' not in ele_classes:
            ele_classes.append('is-invalid')

        field.widget.attrs['class'] = ' '.join(ele_classes)
        return field

    def render(self, context, instance, placeholder):
        field_id = instance.glossary.get('field_id')

        if context.get('user_form'):
            form = context['user_form']
            bound_field = form[field_id]
            if bound_field.errors:
                self.add_error_class(form.fields[field_id])
            context.update({
                'field_id': field_id,
                'field': bound_field,
            })
        return super().render(context, instance, placeholder)
