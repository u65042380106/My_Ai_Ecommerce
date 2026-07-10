# myapp/views.py
import requests
import threading
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User 
from django.core.exceptions import PermissionDenied 
from django.contrib import messages
from django.http import HttpResponse, JsonResponse 
import traceback
from django.views.decorators.csrf import csrf_exempt

# 🌟 เพิ่ม Q เข้ามาสำหรับการค้นหาแบบเงื่อนไข "หรือ (OR)" 🌟
from django.db.models import Count, Q 

from myapp.models import SearchHistory, ComparisonRecord, UserProfile
from .forms import ProfileCompletionForm

@login_required
def complete_profile(request):
    if request.method == 'POST':
        form = ProfileCompletionForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('http://127.0.0.1:8000/')
    else:
        form = ProfileCompletionForm(instance=request.user)
        
    return render(request, 'complete_profile.html', {'form': form})


def index_view(request):
    popular_searches = (
        SearchHistory.objects.values('keyword')
        .annotate(search_count=Count('keyword'))
        .order_by('-search_count')[:10]
    )
    return render(request, 'index.html', {'popular_searches': popular_searches})

@login_required
def search_view(request):
    if hasattr(request.user, 'userprofile') and request.user.userprofile.is_suspended:
        messages.error(request, '❌ บัญชีของคุณถูกระงับการใช้งาน ไม่สามารถใช้ระบบค้นหาสินค้าได้')
        return redirect('http://127.0.0.1:8000/')
        
    return render(request, 'search.html')

@login_required
def profile_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        gender = request.POST.get('gender', '') # รับค่าเพศจากฟอร์ม
        
        if username and username != request.user.username:
            if User.objects.filter(username=username).exists():
                messages.error(request, '❌ ชื่อผู้ใช้นี้มีคนใช้งานแล้ว')
                return redirect('profile')
            request.user.username = username
            
        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.save()
        
        # บันทึกข้อมูลเพศลงใน UserProfile
        if hasattr(request.user, 'userprofile'):
            profile = request.user.userprofile
            # เช็คว่าค่าที่ส่งมาตรงกับ choices หรือไม่ ป้องกัน error
            if gender in ['M', 'F', 'O']:
                profile.gender = gender
            else:
                profile.gender = None
            profile.save()
            
        messages.success(request, '✅ อัปเดตข้อมูลโปรไฟล์เรียบร้อยแล้ว!')
        return redirect('profile')
    return render(request, 'profile.html')

def run_n8n_in_background(history_id, payload):
    try:
        history = SearchHistory.objects.get(id=history_id)
        history.status = 'pending_n8n'
        history.save()

        N8N_WEBHOOK_URL = 'http://localhost:5678/webhook/shopee-search'
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=None)
        
        if response.status_code == 200:
            result_data = response.json()
            
            products_9_items = result_data.get('products', [])
            ai_analysis = result_data.get('ai_analysis', 'ไม่มีผลวิเคราะห์')
            
            history.ai_result = ai_analysis
            
            combined_data = {
                'products': products_9_items,
                'filters': {
                    'min_price': payload.get('min_price', ''),
                    'max_price': payload.get('max_price', ''),
                    'ship_from': payload.get('ship_from', 'all'),
                    'min_rating': payload.get('min_rating', ''),
                    'ai_mode': payload.get('ai_mode', 'balanced')
                }
            }
            history.products_json = json.dumps(combined_data, ensure_ascii=False)
            
            history.status = 'success' 
            history.save()
        else:
            history.status = 'error'
            history.ai_result = "n8n ตอบกลับด้วยสถานะ Error"
            history.save()
            
    except Exception as e:
        try:
            history = SearchHistory.objects.get(id=history_id)
            history.status = 'error'
            history.ai_result = "เกิดข้อผิดพลาดในการเชื่อมต่อระบบวิเคราะห์ข้อมูล"
            history.save()
            print(f"n8n Background Error: {e}")
        except: pass

@login_required
def dashboard_view(request):
    if hasattr(request.user, 'userprofile') and request.user.userprofile.is_suspended:
        messages.error(request, '❌ บัญชีของคุณถูกระงับการใช้งาน ไม่สามารถทำการค้นหาสินค้าได้')
        return redirect('http://127.0.0.1:8000/')

    try:  
        keyword = request.GET.get('keyword', '').strip()
        min_price = request.GET.get('min_price', '').strip()
        max_price = request.GET.get('max_price', '').strip()
        ship_from = request.GET.get('ship_from', 'all')
        min_rating = request.GET.get('min_rating', '').strip()
        ai_mode = request.GET.get('ai_mode', 'balanced')
        
        if not keyword: return redirect('search')
            
        ai_filter_parts = []
        ai_filter_parts.append(f"โปรดวิเคราะห์ชื่อสินค้าเทียบกับ '{keyword}' คัดสแปมทิ้ง และ **คัดเลือกสินค้าที่ดีที่สุดมาให้เหลือเพียง 9 ชิ้นถ้วนเท่านั้น**")

        if min_price: ai_filter_parts.append(f"ราคาตั้งแต่ {min_price} บ.")
        if max_price: ai_filter_parts.append(f"ราคาไม่เกิน {max_price} บ.")
        if ship_from == 'local': ai_filter_parts.append("ส่งจากไทยเท่านั้น")
        elif ship_from == 'overseas': ai_filter_parts.append("ส่งจากต่างประเทศเท่านั้น")
        if min_rating: ai_filter_parts.append(f"รีวิวไม่ต่ำกว่า {min_rating} ดาว")

        if ai_mode == 'safe': ai_filter_parts.append("เน้นน่าเชื่อถือ รีวิวเยอะ")
        elif ai_mode == 'budget': ai_filter_parts.append("เน้นประหยัด คุ้มค่า")
        else: ai_filter_parts.append("จัดเรียงสมดุล ราคา/ความน่าเชื่อถือ")

        ai_filter_text = " และ ".join(ai_filter_parts)
            
        history = SearchHistory.objects.create(
            user=request.user, keyword=keyword, status='pending'
        )
        
        payload = {
            'history_id': history.id,
            'keyword': keyword,
            'min_price': min_price, 'max_price': max_price,
            'ship_from': ship_from, 'min_rating': min_rating, 
            'ai_mode': ai_mode, 'ai_filter': ai_filter_text  
        }
        
        threading.Thread(target=run_n8n_in_background, args=(history.id, payload)).start()
        
        return redirect('loading', history_id=history.id)
    except Exception as e:  
        return HttpResponse(f"Error: {e}")

@login_required
def history_view(request):
    histories = SearchHistory.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'history.html', {'histories': histories})

@login_required
def result_detail_view(request, history_id):
    history = get_object_or_404(SearchHistory, id=history_id, user=request.user)
    latest_comparison = history.comparisons.first()
    
    if latest_comparison:
        return redirect('view_comparison', compare_id=latest_comparison.id)
    else:
        return redirect('select_compare', history_id=history.id)

# --- 🌟 โซน Admin จัดการสมาชิก (เพิ่มระบบค้นหา) 🌟 ---
@login_required
def manage_members_view(request):
    if not request.user.is_staff: raise PermissionDenied
    
    show_deleted = request.GET.get('show_deleted') == 'true'
    search_query = request.GET.get('q', '').strip()
    
    # 1. ดึง UserProfile ทั้งหมดที่ไม่ใช่แอดมิน
    profiles = UserProfile.objects.filter(user__is_staff=False, user__is_superuser=False)
    
    # 2. กรองว่าต้องการแสดงคนถูกลบหรือไม่
    if not show_deleted:
        profiles = profiles.filter(is_deleted=False)
        
    # 3. ถ้ามีการพิมพ์ค้นหา ให้ค้นจาก Username หรือ Email
    if search_query:
        profiles = profiles.filter(
            Q(user__username__icontains=search_query) | 
            Q(user__email__icontains=search_query)
        )
        
    context = {
        'profiles': profiles, 
        'show_deleted': show_deleted,
        'search_query': search_query # ส่งกลับไปแสดงในช่องกรอก
    }
    return render(request, 'manage_members.html', context)

@login_required
def delete_member_view(request, profile_id):
    if not request.user.is_staff: raise PermissionDenied
    if request.method == 'POST':
        profile = get_object_or_404(UserProfile, id=profile_id, user__is_staff=False, user__is_superuser=False)
        profile.soft_delete()
    return redirect('manage_members')

@login_required
def toggle_suspend_view(request, profile_id):
    if not request.user.is_staff: raise PermissionDenied
    if request.method == 'POST':
        profile = get_object_or_404(UserProfile, id=profile_id, user__is_staff=False, user__is_superuser=False)
        profile.is_suspended = not profile.is_suspended
        profile.save()
        
        status = "ระงับบัญชี" if profile.is_suspended else "ปลดระงับ"
    return redirect('manage_members')

@login_required
def delete_history_view(request, history_id):
    if request.method == 'POST':
        history = get_object_or_404(SearchHistory, id=history_id, user=request.user)
        history.delete()
    return redirect('history')

# --- โซนหน้า Loading ---
@login_required
def loading_view(request, history_id):
    history = get_object_or_404(SearchHistory, id=history_id, user=request.user)
    return render(request, 'loading.html', {'history': history})

@login_required
def check_status_view(request, history_id):
    history = get_object_or_404(SearchHistory, id=history_id, user=request.user)
    return JsonResponse({'status': history.status})

# --- โซน Compare ---
@login_required
def select_compare_view(request, history_id):
    history = get_object_or_404(SearchHistory, id=history_id, user=request.user)
    
    try:
        parsed_data = json.loads(history.products_json or '{}')
        if isinstance(parsed_data, dict):
            all_products = parsed_data.get('products', [])
        elif isinstance(parsed_data, list):
            all_products = parsed_data
        else:
            all_products = []
    except (json.JSONDecodeError, TypeError):
        all_products = []

    if request.method == 'POST':
        selected_indexes = request.POST.getlist('selected_products')
        
        if len(selected_indexes) < 2:
            messages.warning(request, 'กรุณาเลือกสินค้าอย่างน้อย 2 ชิ้นเพื่อทำการเปรียบเทียบ')
            return redirect('select_compare', history_id=history_id)

        try:
            selected_products = [all_products[int(idx)] for idx in selected_indexes]
        except (IndexError, ValueError):
            messages.error(request, 'เกิดข้อผิดพลาดในการเลือกสินค้า')
            return redirect('select_compare', history_id=history_id)

        ai_recommendation = "กำลังวิเคราะห์..."
        
        try:
            N8N_COMPARE_WEBHOOK = 'http://localhost:5678/webhook/compare-items' 
            
            resp = requests.post(N8N_COMPARE_WEBHOOK, json={
                "keyword": history.keyword,
                "items": selected_products
            }, timeout=60) 
            
            if resp.status_code == 200:
                try:
                    result_data = resp.json()
                except json.JSONDecodeError:
                    result_data = json.loads(resp.text)
                
                ai_recommendation = result_data.get('recommendation', "การเปรียบเทียบเสร็จสิ้น")
                best_url = result_data.get('best_choice_url', "")
                
                for p in selected_products:
                    product_link = p.get('link', p.get('url', ''))
                    if product_link and product_link == best_url:
                        p['is_best_choice'] = True
                    else:
                        p['is_best_choice'] = False
            else:
                ai_recommendation = "ระบบ AI ขัดข้องชั่วคราว ไม่สามารถสร้างคำแนะนำได้"
        except Exception as e:
            print("N8N Error:", e)
            ai_recommendation = "ไม่สามารถเชื่อมต่อกับ AI N8N ได้ (ตรวจสอบ Webhook)"

        new_comparison = ComparisonRecord.objects.create(
            history=history,
            selected_items_json=json.dumps(selected_products, ensure_ascii=False),
            ai_recommendation=ai_recommendation
        )
        
        return redirect('view_comparison', compare_id=new_comparison.id)

    return render(request, 'select_compare.html', {
        'keyword': history.keyword,
        'all_products': all_products,
        'history_id': history_id
    })

@login_required
def view_comparison_view(request, compare_id):
    comparison = get_object_or_404(ComparisonRecord, id=compare_id, history__user=request.user)
    
    try:
        selected_products = json.loads(comparison.selected_items_json)
    except:
        selected_products = []

    for item in selected_products:
        if isinstance(item, dict):
            item['product_url'] = item.get('link') or item.get('url') or ''

    return render(request, 'view_comparison.html', {
        'keyword': comparison.history.keyword,
        'selected_products': selected_products,
        'ai_recommendation': comparison.ai_recommendation,
        'history_id': comparison.history.id 
    })

@login_required
def edit_profile(request):
    return complete_profile(request)


@login_required
def admin_stats_view(request):
    # ตรวจสอบว่าเป็นแอดมินหรือทีมงานหรือไม่ ป้องกันผู้ใช้ทั่วไปเข้าถึง
    if not request.user.is_staff:
        raise PermissionDenied

    # 1. สรุปจำนวนผู้ใช้ทั้งหมด แยกสถานะเป็นตัวเลข
    total_users = UserProfile.objects.filter(is_deleted=False).count()
    normal_users = UserProfile.objects.filter(is_deleted=False, is_suspended=False).count()
    suspended_users = UserProfile.objects.filter(is_deleted=False, is_suspended=True).count()

    # 2. นับจำนวนผู้ใช้แยกตามเพศ
    male_users = UserProfile.objects.filter(is_deleted=False, gender='M').count()
    female_users = UserProfile.objects.filter(is_deleted=False, gender='F').count()
    # นับคนเลือกอื่นๆ หรือคนที่ยังไม่ได้กรอก/ค่าว่าง
    other_users = UserProfile.objects.filter(is_deleted=False).filter(
        Q(gender='O') | Q(gender__isnull=True) | Q(gender='')
    ).count()

    # 3. สถิติ Top 10 คำค้นหายอดนิยมของเว็บไซต์ทั้งหมด
    top_keywords_query = SearchHistory.objects.values('keyword').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    top_keywords_labels = [item['keyword'] for item in top_keywords_query]
    top_keywords_data = [item['total'] for item in top_keywords_query]

    # 4. สถิติ Top 10 คำค้นหาแยกตามเพศชายและหญิง สำหรับกราฟแท่งแนวนอน
    male_keyword_data = []
    female_keyword_data = []
    
    for kw in top_keywords_labels:
        m_count = SearchHistory.objects.filter(keyword=kw, user__userprofile__gender='M').count()
        f_count = SearchHistory.objects.filter(keyword=kw, user__userprofile__gender='F').count()
        male_keyword_data.append(m_count)
        female_keyword_data.append(f_count)

    context = {
        'total_users': total_users,
        'normal_users': normal_users,
        'suspended_users': suspended_users,
        
        'male_users': male_users,
        'female_users': female_users,
        'other_users': other_users,
        
        # แปลงเป็น JSON string เพื่อให้ JavaScript รับค่าไปวาดกราฟได้ง่ายและปลอดภัย
        'top_keywords_labels': json.dumps(top_keywords_labels, ensure_ascii=False),
        'top_keywords_data': json.dumps(top_keywords_data),
        
        'male_keyword_data': json.dumps(male_keyword_data),
        'female_keyword_data': json.dumps(female_keyword_data),
    }
    return render(request, 'admin_stats.html', context)

@csrf_exempt
def update_status_api(request, history_id):
    """ API สำหรับให้ n8n ยิง Webhook กลับมาเพื่ออัปเดตสถานะ Progress Bar """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status')
            
            if new_status:
                history = SearchHistory.objects.get(id=history_id)
                history.status = new_status
                history.save()
                return JsonResponse({'status': 'success', 'updated_to': new_status})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid request'}, status=400)