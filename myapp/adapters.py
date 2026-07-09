# myapp/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.conf import settings
from django.shortcuts import redirect

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def _is_admin_email(self, email):
        admin_emails = [admin_email.lower() for admin_email in getattr(settings, 'ADMIN_EMAILS', [])]
        return bool(email) and email.lower() in admin_emails
    
    
    # ทำงานเมื่อ "สมัครสมาชิกใหม่" ผ่าน Google ครั้งแรก
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        
        # ตรวจสอบว่าอีเมลของผู้ใช้รายนี้ อยู่ในรายชื่อ ADMIN_EMAILS หรือไม่
        if self._is_admin_email(user.email):
            user.is_staff = True        # ให้สิทธิ์เข้าหน้าแอดมินหลังบ้าน
            user.is_superuser = True    # ให้สิทธิ์แอดมินสูงสุดทำได้ทุกอย่าง
            user.save()
        return user

    def is_open_for_signup(self, request, sociallogin):
        user = sociallogin.user
        if self._is_admin_email(getattr(user, 'email', '')):
            raise ImmediateHttpResponse(redirect('account_login'))
        return super().is_open_for_signup(request, sociallogin)
            
    # ทำงานเมื่อ "ล็อกอินซ้ำ" ในครั้งต่อๆ ไป (เผื่อกรณีเราเพิ่งแอดอีเมลเขาเป็นแอดมินทีหลัง)
    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        if not user.id and self._is_admin_email(user.email):
            raise ImmediateHttpResponse(redirect('account_login'))

        if user.id and self._is_admin_email(user.email):
            if not user.is_staff or not user.is_superuser:
                user.is_staff = True
                user.is_superuser = True
                user.save()
