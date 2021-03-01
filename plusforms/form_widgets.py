import random

from django import forms
from django.core import signing


class CaptchaInputWidget(forms.TextInput):
    def get_context(self, name, value, attrs):
        # delete initial input value
        return super(CaptchaInputWidget, self).get_context(name, value, attrs)


class CaptchaWidget(forms.MultiWidget):
    template_name = 'plusforms/widgets/captcha/captcha.html'

    def __init__(self, attrs=None):
        widgets = [
            CaptchaOperationWidget(attrs=attrs),
            CaptchaInputWidget(attrs=attrs),
        ]
        super().__init__(widgets=widgets, attrs=attrs)

    def decompress(self, value):
        if value:
            value_signed, value = value
            return value_signed, value
        return [None, None]


class CaptchaOperationWidget(forms.HiddenInput):
    template_name = 'plusforms/widgets/captcha/captcha_hidden.html'

    OP_PLUS = '+'
    OP_MINUS = '-'
    OP_MULTIPLY = '*'

    OPERATIONS = [
        OP_PLUS,
        OP_MINUS,
        OP_MULTIPLY,
    ]

    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.operation = CaptchaOperationWidget.operation()
        self.operation_result_signed = CaptchaOperationWidget._operation_result_signed(self.operation)

    @staticmethod
    def calc_operation(operation):
        x, op, y = operation
        result = None

        if op == CaptchaOperationWidget.OP_PLUS:
            result = x + y
        elif op == CaptchaOperationWidget.OP_MINUS:
            result = x - y
        elif op == CaptchaOperationWidget.OP_MULTIPLY:
            result = x * y

        return result

    @staticmethod
    def operation():
        x = random.randint(1, 12)
        y = random.randint(1, 12)
        op = random.choice(CaptchaOperationWidget.OPERATIONS)

        # change values if minus operation
        if op == CaptchaOperationWidget.OP_MINUS:
            if x < y:
                _y = y
                y = x
                x = _y
        return [x, op, y]

    @staticmethod
    def _operation_result_signed(operation):
        result = CaptchaOperationWidget.calc_operation(operation)
        return signing.dumps(result)

    def get_context(self, name, value, attrs):
        value = self.operation_result_signed
        context = super().get_context(name, value, attrs)
        context['widget']['operation'] = self.operation
        return context
