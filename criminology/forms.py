from django import forms
import datetime
from .models import TableOfSpecification


class AcademicYearForm(forms.Form):
    
    def generate_years():
        start_year = 2024 
        num_years = 5   
        years = [(str(year), str(year)) for year in range(start_year, start_year + num_years)]
        return years

    academic_year = forms.ChoiceField(
        choices=generate_years(),
        label='Select Academic Year',
        widget=forms.Select(attrs={'class': 'form-control'}) 
    )


class TableOfSpecificationForm(forms.ModelForm):
    class Meta:
        model = TableOfSpecification
        fields = ['academic_year', 'subject', 'topic', 'subtopic', 'pwd', 
                  'understanding', 'remembering', 'analyzing', 'creating', 
                  'evaluating', 'applying']
        




