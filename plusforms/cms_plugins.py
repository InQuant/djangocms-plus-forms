from pprint import pprint

from cms.plugin_pool import plugin_pool
from cmsplus.plugin_base import PlusPluginBase, PlusPluginFormBase
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from plusforms.form_fields import get_available_form_fields, get_class
from plusforms.models import SubmittedForm


class GenericFormPluginForm(PlusPluginFormBase):
    form_id = forms.SlugField(label=_('Form identifier'), required=True)

    success_text = forms.CharField(label=_('Success text'), widget=forms.Textarea)
    button_text = forms.CharField(label=_('Submit button text'), required=True, initial=_('Submit'))

    name = forms.CharField(label=_('Name'), required=False)
    description = forms.CharField(label=_('Description'), required=False, widget=forms.Textarea)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@plugin_pool.register_plugin
class GenericFormPlugin(PlusPluginBase):
    cache = False
    form = GenericFormPluginForm
    name = _('Form')
    module = 'form'
    allow_children = True
    render_template = 'plusforms/base_form.html'

    @staticmethod
    def field_plugins(instance):
        children = []
        for child in instance.child_plugin_instances or []:
            if child.plugin_type == 'GenericFieldPlugin':
                children.append(child)
        return children

    def process_submit(self, context, instance):
        request = context.get('request')

        form_data = {}
        if not request.POST.get('form-%s' % instance.id):
            return

        for child in self.field_plugins(instance):
            ci, cc = child.get_plugin_instance()

            field = cc.get_form_field(context, ci)
            value = request.POST.get(field.widget.name)

            try:
                field.clean(value)
            except ValidationError:
                return

            form_data[field.widget.name] = value

        pprint(request.META)
        obj = SubmittedForm.objects.create(
            by_user=request.user if request.user.is_authenticated else None,
            form=instance,
            form_data=form_data,
            meta_data={
                'host': request.META.get('HTTP_HOST'),
                'origin': request.META.get('HTTP_ORIGIN'),
                'referrer': request.META.get('HTTP_REFERER'),
                'user_agent': request.META.get('HTTP_USER_AGENT'),
                'remote_ip': get_client_ip(request),
            }
        )
        if not obj:
            return

        request.POST = {}
        return True

    @classmethod
    def get_identifier(cls, instance):
        return "%s" % (
            instance.glossary.get('name'),
        )

    def render(self, context, instance, placeholder):
        if self.process_submit(context, instance):
            context['success'] = True
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
    parent_classes = ['GenericFormPlugin', ]
    allow_children = True
    form = FormFieldPluginForm

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

    def get_form_field(self, context, instance):
        request = context.get('request')
        FIELD_CLASS = self.get_field_class(instance)
        data = instance.glossary
        field_id = data.get('field_id', None)

        _attrs = {
            'placeholder': data.get('field_placeholder', ''),
            'id': field_id,
            'class': getattr(FIELD_CLASS, 'widget_class', ''),
        }
        input_type = getattr(FIELD_CLASS.widget, 'input_type', '')

        widget_value = None
        if request.POST.get('form-%s' % instance.parent_id):
            widget_value = request.POST.get(field_id)

        if input_type == 'checkbox':
            if widget_value:
                _attrs['checked'] = True

        widget = FIELD_CLASS.widget(attrs=_attrs)
        if input_type != 'checkbox':
            widget.value = widget_value
        widget.name = field_id
        widget.type = input_type

        field_kwargs = {
            'label': data.get('label', ''),
            'help_text': data.get('help_text', data.get('value')),
            'widget': widget,
            'required': data.get('required', False),
        }

        return FIELD_CLASS(**field_kwargs)

    @staticmethod
    def add_error_class(field):
        ele_classes = field.widget.attrs.get('class', '').split(' ')
        if 'is-invalid' not in ele_classes:
            ele_classes.append('is-invalid')

        field.widget.attrs['class'] = ' '.join(ele_classes)
        return field

    def render(self, context, instance, placeholder):
        request = context.get('request')
        field = self.get_form_field(context, instance)
        value = request.POST.get(field.widget.name)

        if request.POST and request.POST.get('form-%s' % instance.parent_id):
            try:
                value = field.clean(value)
            except ValidationError as e:
                context['errors'] = e
                self.add_error_class(field)

        context['field'] = field
        return super(GenericFieldPlugin, self).render(context, instance, placeholder)
