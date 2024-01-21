from django.contrib import admin
from django.contrib.admin.options import forms
from meshapi.models import Building, Member, Install

admin.site.site_header = "MeshDB Admin"
admin.site.site_title = "MeshDB Admin Portal"
admin.site.index_title = "Welcome to MeshDB Admin Portal"

# Register your models here.

#admin.site.register(Building)
admin.site.register(Member)
admin.site.register(Install)

class BuildingAdminForm(forms.ModelForm):
    class Meta:
        model = Building
        fields = '__all__'
        widgets = {
            'street_address': forms.TextInput(),
            'city': forms.TextInput(),
            'state': forms.TextInput(),
            'zip_code': forms.NumberInput(),
            'node_name': forms.TextInput(),
            'street_address': forms.TextInput(),
        }

@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    form = BuildingAdminForm

