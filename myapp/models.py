# myapp/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ผู้ใช้งาน")
    keyword = models.CharField(max_length=255, verbose_name="คำค้นหา")
    ai_result = models.TextField(blank=True, null=True, verbose_name="ผลวิเคราะห์จาก AI")
    
    # เพิ่มฟิลด์เก็บรายการสินค้าในรูปแบบข้อความ JSON
    products_json = models.TextField(blank=True, default="[]", verbose_name="สินค้าดิบจาก Lazada")
    
    # เพิ่มสถานะการทำงาน: pending (กำลังรอ), success (เสร็จแล้ว), error (ระบบล่ม)
    status = models.CharField(max_length=20, default='pending', verbose_name="สถานะ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันเวลาที่ค้นหา")

    class Meta:
        ordering = ['-created_at']

class ComparisonRecord(models.Model):
    history = models.ForeignKey(SearchHistory, on_delete=models.CASCADE, related_name='comparisons')
    selected_items_json = models.TextField(verbose_name="ข้อมูลสินค้าที่เลือกเปรียบเทียบ (JSON)")
    ai_recommendation = models.TextField(blank=True, null=True, verbose_name="คำแนะนำจาก AI")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] # ให้เรียงจากล่าสุดไปเก่าสุด

class UserProfile(models.Model):
    GENDER_CHOICES = [
        ('M', 'ชาย'),
        ('F', 'หญิง'),
        ('O', 'อื่นๆ/ไม่ระบุ'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    is_complete = models.BooleanField(default=False) # เช็กว่ากรอกครบหรือยัง
    is_suspended = models.BooleanField(default=False, verbose_name="สถานะระงับบัญชี")
    is_deleted = models.BooleanField(default=False, verbose_name="สถานะถูกลบ")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="ลบเมื่อวันที่")

    def soft_delete(self):
        """ ฟังก์ชันสำหรับทำ Soft Delete """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        # จะให้เข้าสู่ระบบไม่ได้เลยด้วยก็ได้ โดยการ set is_active = False ของ User หลัก
        self.user.is_active = False 
        self.user.save()
        self.save()

    def __str__(self):
        return self.user.username

# ใช้ Signal เพื่อสร้าง Profile อัตโนมัติเมื่อ Google สร้าง User ใหม่
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)