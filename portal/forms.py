"""Formulaire dynamique = exactement les champs décrits dans le module concerné."""
from django import forms


def create_profile_form(module, data=None):
    attrs = {}
    for field in module.fields:
        css = 'input-control'
        kw = {'label': field.label, 'required': True, 'help_text': field.help}
        if field.kind == 'select':
            attrs[field.key] = forms.ChoiceField(
                choices=[('', 'Choisir une option'), *field.choices],
                widget=forms.Select(attrs={'class': css}), **kw
            )
        elif field.kind == 'decimal':
            attrs[field.key] = forms.DecimalField(
                min_value=field.minimum, max_value=field.maximum,
                widget=forms.NumberInput(attrs={'class': css, 'placeholder': field.placeholder, 'step': 'any'}), **kw
            )
        else:
            attrs[field.key] = forms.IntegerField(
                min_value=field.minimum, max_value=field.maximum,
                widget=forms.NumberInput(attrs={'class': css, 'placeholder': field.placeholder}), **kw
            )
    DynamicForm = type(f'{module.slug.title()}ProfileForm', (forms.Form,), attrs)
    return DynamicForm(data=data)
