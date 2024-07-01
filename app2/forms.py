from django import forms
from .models import Medicine, Medical, Room

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['room_type', 'price', 'quantity']

    def clean(self):
        cleaned_data = super().clean()
        room_type = cleaned_data.get('room_type')
        quantity = cleaned_data.get('quantity')

        if room_type and quantity:
            booked_rooms = Room.objects.filter(room_type=room_type).count()
            if booked_rooms >= quantity:
                raise forms.ValidationError(f"Not enough {room_type} rooms available. Choose a lower quantity.")
        
        return cleaned_data

class SetPasswordForm(forms.Form):
    new_password1 = forms.CharField(label='New password', widget=forms.PasswordInput)
    new_password2 = forms.CharField(label='Confirm new password', widget=forms.PasswordInput)
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match.")

        return cleaned_data

class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ['name', 'quantity', 'price']
        
    def clean_medicine_id(self):
        medicine_id = self.cleaned_data['medicine_id']
        if Medicine.objects.filter(medicine_id=medicine_id).exists():
            raise forms.ValidationError("Medicine with this ID already exists.")
        return medicine_id
        
class AssignMedicineForm(forms.ModelForm):
    class Meta:
        model = Medical
        fields = ['medicine', 'quantity']

    def __init__(self, *args, **kwargs):
        doctor = kwargs.pop('doctor', None)
        super(AssignMedicineForm, self).__init__(*args, **kwargs)
        if doctor:
            self.fields['medicine'].queryset = Medicine.objects.all()
