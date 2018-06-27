from django import forms
from django.utils.safestring import mark_safe
from .models import Document

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ('name', 'document', 'onestop_id')

    def __init__(self, *args, **kwargs):
        super(DocumentForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class' : 'form-control', 'placeholder' : 'Name of Transit System'})
        self.fields['document'].widget.attrs.update({'class' : 'form-control', 'placeholder' : 'GTFS .zip File'})
        self.fields['onestop_id'].widget.attrs.update({'class' : 'form-control', 'placeholder' : 'Transitland Onestop ID'})

        self.fields['document'].label = mark_safe("GTFS zip file<a href=# data-toggle='modal' data-target='#gtfsModal'><sup>[?]</sup></a>")
        self.fields['onestop_id'].label = mark_safe("Optional Transitland Onestop ID<a href=# data-toggle='modal' data-target='#onestopModal'><sup>[?]</sup></a>")