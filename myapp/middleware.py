# myapp/middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # รายชื่อ URL ที่อนุญาตให้เข้าได้แม้ยังกรอกไม่ครบ
            allowed_urls = [
                reverse('complete_profile'), 
                reverse('account_logout') # เปลี่ยนเป็น account_logout สำหรับ allauth
            ]
            
            # ถ้าไม่ได้อยู่ในหน้าพวกนี้ ให้ตรวจสถานะ
            if request.path not in allowed_urls and not request.path.startswith('/admin/'):
                profile = getattr(request.user, 'userprofile', None)
                if not profile or not profile.is_complete:
                    return redirect('complete_profile') # เด้งกลับไปหน้าบังคับกรอก
        
        response = self.get_response(request)
        return response