# myproject/urls.py
from django.contrib import admin
from django.urls import path, include
from myapp import views
from django.shortcuts import redirect

urlpatterns = [
    # --- หน้าหลักและระบบล็อกอิน ---
    path('admin/', admin.site.urls),
    path('', views.index_view, name='index'), 
    path('accounts/', include('allauth.urls')),
    path('profile/', views.profile_view, name='profile'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    
    # --- ระบบค้นหาและ Dashboard ---
    path('search/', views.search_view, name='search'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/<int:history_id>/', views.result_detail_view, name='result_detail'),
    
    # --- จัดการสมาชิก (Admin) ---
    path('manage-members/', views.manage_members_view, name='manage_members'),
    path('delete-member/<int:user_id>/', views.delete_member_view, name='delete_member'),
    
    # --- ประวัติการค้นหา ---
    path('history/', views.history_view, name='history'),
    path('history/delete/<int:history_id>/', views.delete_history_view, name='delete_history'),
    
    # --- หน้ารอโหลดสถานะ (AJAX) ---
    path('loading/<int:history_id>/', views.loading_view, name='loading'),
    path('api/check_status/<int:history_id>/', views.check_status_view, name='check_status'),
    
    # --- ระบบเปรียบเทียบ (Compare) โครงสร้างใหม่ ---
    path('select-compare/<int:history_id>/', views.select_compare_view, name='select_compare'),
    path('view-comparison/<int:compare_id>/', views.view_comparison_view, name='view_comparison'),

    # 🌟 1. ดักจับหน้า login ของ admin ให้เด้งมาที่หน้า login ของระบบเรา พร้อมส่ง parameter next=/admin/ 
    # เพื่อให้พอล็อกอินเสร็จ จะได้เด้งกลับไปที่หน้า Dashboard ของ Admin ทันที
    path('admin/login/', lambda request: redirect('/accounts/login/?next=/admin/')),
    
    path('admin/', admin.site.urls),
    
    # ... URL อื่นๆ ที่มีอยู่แล้ว ...
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('accounts/', include('allauth.urls')),

    path('manage-members/', views.manage_members_view, name='manage_members'),
    path('manage-members/delete/<int:profile_id>/', views.delete_member_view, name='delete_member'),
    path('manage-members/suspend/<int:profile_id>/', views.toggle_suspend_view, name='toggle_suspend'),
]