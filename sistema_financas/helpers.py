"""Helpers compartilhados usados pelos apps (forms Bootstrap, mensagens)."""
from django.contrib import messages
from django.forms.widgets import CheckboxInput, CheckboxSelectMultiple


class BootstrapFormMixin:
    """Adiciona classes CSS do Bootstrap 5 a todos os inputs do form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            existing = widget.attrs.get('class', '')
            if isinstance(widget, (CheckboxInput, CheckboxSelectMultiple)):
                widget.attrs['class'] = ('form-check-input ' + existing).strip()
            else:
                widget.attrs['class'] = ('form-control ' + existing).strip()


def success_message(request, texto):
    messages.success(request, texto)


def erro_message(request, texto):
    messages.error(request, texto)