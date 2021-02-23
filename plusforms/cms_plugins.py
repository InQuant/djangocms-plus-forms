import abc
import logging

from cms.plugin_pool import plugin_pool
from cmsplus.models import PlusPlugin
from cmsplus.plugin_base import PlusPluginBase, PlusPluginFormBase
from django import forms
from django.conf import settings
from django.core.validators import get_available_image_extensions
from django.utils.translation import ugettext_lazy as _

from plusforms.form_fields import get_available_form_fields, get_class
from plusforms.forms import PlusFormBase
from plusforms.models import SubmittedForm

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

    @abc.abstractmethod
    def pre_save(self, request, context, instance, plus_form: PlusFormBase):
        """
        Hook to customize what to do (maybe additional data cleaning) before object creation and after clean.
        """

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
                    self.pre_save(request, context, instance, self.user_form)
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
        self.fields['field_type'].choices = self.get_field_type_choices


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
        if self.render_template:
            return self.render_template
        CLS = self.get_field_class(instance)
        if hasattr(CLS, 'template_name'):
            return CLS.template_name
        else:
            return CLS.widget.template_name

    @classmethod
    def get_identifier(cls, instance):
        return "%s %s".strip() % (
            instance.glossary.get('field_type'),
            instance.glossary.get('label')
        )

    @classmethod
    def get_form_field(cls, context, instance):
        FIELD_CLASS = cls.get_field_class(instance)
        return FIELD_CLASS.bound_field(instance.glossary)

    @staticmethod
    def add_error_class(field):
        ele_classes = field.widget.attrs.get('class', '').split(' ')
        if 'is-invalid' not in ele_classes:
            ele_classes.append('is-invalid')

        field.widget.attrs['class'] = ' '.join(ele_classes)
        return field

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        field_id = instance.glossary.get('field_id')

        if context.get('user_form'):
            form = context['user_form']
            try:
                bound_field = form[field_id]
            except KeyError as e:
                logger.error(str(e))
                return context

            if bound_field.errors:
                self.add_error_class(form.fields[field_id])
            context.update({
                'field_id': field_id,
                'field': bound_field,
            })
        return context
