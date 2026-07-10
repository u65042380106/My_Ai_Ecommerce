# myproject/urls.py
from django.contrib import admin
from django.urls import path, include
from myapp import views
from django.shortcuts import redirect

urlpatterns = [
    # 🌟 1. ดักจับหน้า login ของ admin
    path('admin/login/', lambda request: redirect('/accounts/login/?next=/admin/')),
    
    # 🌟 2. ต้องวางหน้าสถิติ (admin/stats/) ไว้ "ก่อน" Django Admin เสมอ
    path('admin/stats/', views.admin_stats_view, name='admin_stats'),
    
    # 3. URL ของ Django Admin เดิม
    path('admin/', admin.site.urls),
    
    # --- หน้าหลักและระบบล็อกอิน ---
    path('', views.index_view, name='index'), 
    path('accounts/', include('allauth.urls')),
    path('profile/', views.profile_view, name='profile'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    
    # --- ระบบค้นหาและ Dashboard ---
    path('search/', views.search_view, name='search'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/<int:history_id>/', views.result_detail_view, name='result_detail'),
    
    # --- ประวัติการค้นหา ---
    path('history/', views.history_view, name='history'),
    path('history/delete/<int:history_id>/', views.delete_history_view, name='delete_history'),
    
    # --- 🌟 โซนจัดการผู้ดูแลระบบ (Admin) 🌟 ---
    path('manage-members/', views.manage_members_view, name='manage_members'),
    path('manage-members/delete/<int:profile_id>/', views.delete_member_view, name='delete_member'),
    path('manage-members/suspend/<int:profile_id>/', views.toggle_suspend_view, name='toggle_suspend'),
    
    # --- หน้ารอโหลดสถานะ (AJAX) ---
    path('loading/<int:history_id>/', views.loading_view, name='loading'),
    path('api/check_status/<int:history_id>/', views.check_status_view, name='check_status'),
    
    # --- ระบบเปรียบเทียบ (Compare) โครงสร้างใหม่ ---
    path('select-compare/<int:history_id>/', views.select_compare_view, name='select_compare'),
    path('view-comparison/<int:compare_id>/', views.view_comparison_view, name='view_comparison'),

    path('api/update_status/<int:history_id>/', views.update_status_api, name='update_status_api'),
]