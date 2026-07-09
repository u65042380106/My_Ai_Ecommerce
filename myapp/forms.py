# myapp/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

class ProfileCompletionForm(forms.ModelForm):
    # กำหนดให้ต้องกรอกข้อมูล (required=True)
    first_name = forms.CharField(max_length=30, required=True, label='ชื่อจริง')
    last_name = forms.CharField(max_length=30, required=True, label='นามสกุล')
    gender = forms.ChoiceField(choices=UserProfile.GENDER_CHOICES, required=True, label='เพศ')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ดึงค่าเพศมาแสดง (กรณีเป็นหน้าแก้ไขโปรไฟล์)
        if hasattr(self.instance, 'userprofile') and self.instance.userprofile.gender:
            self.fields['gender'].initial = self.instance.userprofile.gender

    def save(self, commit=True):
        user = super().save(commit)
        # บันทึกข้อมูลเพศและเปลี่ยนสถานะว่ากรอกครบแล้ว
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.gender = self.cleaned_data['gender']
        profile.is_complete = True
        if commit:
            profile.save()
        return user