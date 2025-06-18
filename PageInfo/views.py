from datetime import datetime, timedelta  # ใส่ไว้บนสุดของ views.py ด้วย
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Prefetch
from django.conf import settings
from .models import PageGroup, PageInfo, FacebookPost, FollowerHistory
from .forms import PageGroupForm, PageURLForm
from .fb_page_info import PageInfo as FBPageInfo
from .fb_page_info import PageFollowers  # ✅ เพิ่มบรรทัดนี้
from .tiktok_page_info import get_tiktok_info  # แก้เป็น import get_tiktok_info
from .ig_page_info import get_instagram_info
from .lm8_page_info import get_lemon8_info  # ✅ เพิ่มบรรทัดนี้
from .yt_page_info import get_youtube_info
from .fb_post_info import run_fb_post_scraper  # ✅ ถูก: ใช้ชื่อไฟล์ที่แท้จริง
from collections import Counter
from collections import defaultdict
import calendar
import re
import os
import json  # 👈 ต้อง import นี้

def extract_top_hashtags(posts, top_n=50):
    hashtag_counter = Counter()
    for post in posts:
        content = getattr(post, 'post_content', '') or ''
        hashtags = re.findall(r"#\S+", content)
        for tag in hashtags:
            hashtag_counter[tag.lower()] += 1
    return hashtag_counter.most_common(top_n)

def clean_number(value):
    if isinstance(value, str):
        value = value.lower().replace(',', '').replace(' videos', '').replace(' views', '').replace(' subscribers', '').strip()
        if 'k' in value:
            return int(float(value.replace('k', '')) * 1_000)
        elif 'm' in value:
            return int(float(value.replace('m', '')) * 1_000_000)
        elif 'b' in value:
            return int(float(value.replace('b', '')) * 1_000_000_000)
        try:
            return int(value)
        except ValueError:
            return 0
    elif isinstance(value, (int, float)):
        return int(value)
    else:
        return 0


def add_page(request, group_id):
    group = PageGroup.objects.get(id=group_id)

    if request.method == 'POST':
        form = PageURLForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data['url']
            platform = form.cleaned_data['platform']
            allowed_fields = {f.name for f in PageInfo._meta.get_fields()}

            if platform == 'facebook':
                    fb_data = FBPageInfo(url)
                    if 'page_id' in fb_data:
                        follower_data = PageFollowers(fb_data['page_id'])
                        if follower_data:
                            fb_data.update(follower_data)
                    filtered_data = {k: v for k, v in fb_data.items() if k in allowed_fields}
                    for key in ['page_likes_count', 'page_followers_count']:
                        value = filtered_data.get(key)
                        if isinstance(value, str):
                            filtered_data[key] = int(value.replace(',', ''))
                    filtered_data['platform'] = 'facebook'

                    # ✅ ดึงโพสต์ + บันทึกโพสต์
                    page_obj = PageInfo.objects.create(page_group=group, **filtered_data)

                    # ✅ ดึงโพสต์ + บันทึกโพสต์
                    try:
                        cutoff_date = datetime.now() - timedelta(days=30)
                        cookie_path = os.path.join(settings.BASE_DIR, 'PageInfo', 'cookie.json')

                        posts = run_fb_post_scraper(url, cookies_path=cookie_path, cutoff_dt=cutoff_date)

                        for post in posts or []:  # เผื่อ posts เป็น None
                            FacebookPost.objects.create(
                                page=page_obj,
                                post_id=post['post_id'],
                                post_timestamp_dt=post['post_timestamp_dt'],
                                post_timestamp_text=post['post_timestamp_text'],
                                post_content=post['post_content'],
                                post_imgs=post['post_imgs'],
                                reactions=post['reactions'],
                                comment_count=post['comment_count'],
                                share_count=post['share_count']
                            )
                    except Exception as e:
                        print("❌ Error fetching posts:", e)


            elif platform == 'tiktok':
                tiktok_data = get_tiktok_info(url)
                if tiktok_data:
                    filtered_data = {
                        'page_username': tiktok_data.get('username'),
                        'page_name': tiktok_data.get('nickname'),
                        'page_followers': tiktok_data.get('followers'),
                        'page_likes': tiktok_data.get('likes'),
                        'page_description': tiktok_data.get('bio'),
                        'profile_pic': tiktok_data.get('profile_pic'),
                        'page_url': tiktok_data.get('url'),
                        'platform': 'tiktok'
                    }
                    filtered_data = {k: v for k, v in filtered_data.items() if k in allowed_fields}
                    PageInfo.objects.create(page_group=group, **filtered_data)
                else:
                    form.add_error(None, "❌ ไม่สามารถดึงข้อมูล TikTok ได้ กรุณาตรวจสอบ URL หรือรอสักครู่")
                    return render(request, 'PageInfo/add_page.html', {'form': form, 'group': group})


            elif platform == 'instagram':

                match = re.search(r"instagram\.com/([\w\.\-]+)/?", url)

                if match:

                    username = match.group(1)

                    ig_data = get_instagram_info(username)

                    if ig_data:

                        filtered_data = {

                            'page_username': ig_data.get('username'),

                            'page_name': ig_data.get('username'),

                            'page_followers': ig_data.get('followers_count'),

                            'page_website': ig_data.get('website'),

                            'page_category': ig_data.get('category'),

                            'post_count': ig_data.get('post_count'),

                            'page_description': ig_data.get('bio'),

                            'profile_pic': ig_data.get('profile_pic'),

                            'page_url': ig_data.get('url'),

                            'platform': 'instagram'

                        }

                        filtered_data = {k: v for k, v in filtered_data.items() if k in allowed_fields}

                        PageInfo.objects.create(page_group=group, **filtered_data)

                    else:

                        form.add_error(None, "❌ ไม่สามารถดึงข้อมูล Instagram ได้ กรุณาตรวจสอบ URL หรือรอสักครู่")

                        return render(request, 'PageInfo/add_page.html', {'form': form, 'group': group})

                else:

                    form.add_error(None, "❌ URL Instagram ไม่ถูกต้อง")

                    return render(request, 'PageInfo/add_page.html', {'form': form, 'group': group})


            elif platform == 'lemon8':

                lm8_data = get_lemon8_info(url)  # ใช้ url เต็ม ไม่ต้องตัด username

                if lm8_data:

                    allowed_fields = {f.name for f in PageInfo._meta.get_fields()}

                    filtered_data = {

                        'page_username': lm8_data.get('username'),

                        'page_name': lm8_data.get('username'),

                        'page_followers': lm8_data.get('followers_count'),

                        'page_likes': lm8_data.get('likes_count'),

                        'following_count': lm8_data.get('following_count'),

                        'age': lm8_data.get('age'),

                        'page_description': lm8_data.get('bio'),

                        'page_website': lm8_data.get('website'),

                        'profile_pic': lm8_data.get('profile_pic'),

                        'page_url': lm8_data.get('url'),

                        'platform': 'lemon8'

                    }

                    filtered_data = {k: v for k, v in filtered_data.items() if k in allowed_fields}

                    PageInfo.objects.create(page_group=group, **filtered_data)

                else:

                    form.add_error(None, "❌ ไม่สามารถดึงข้อมูล Lemon8 ได้ กรุณาตรวจสอบ URL หรือรอสักครู่")

                    return render(request, 'PageInfo/add_page.html', {'form': form, 'group': group})




            elif platform == 'youtube':

                from .yt_page_info import get_youtube_info

                yt_data = get_youtube_info(url)

                if yt_data:

                    allowed_fields = {f.name for f in PageInfo._meta.get_fields()}

                    yt_data['subscribers_count'] = clean_number(yt_data.get('subscribers_count'))

                    yt_data['videos_count'] = clean_number(yt_data.get('videos_count'))

                    yt_data['total_views'] = clean_number(yt_data.get('total_views'))

                    filtered_data = {

                        'page_username': yt_data.get('username'),

                        'page_name': yt_data.get('page_name'),

                        'page_followers': yt_data.get('subscribers_count'),

                        'profile_pic': yt_data.get('profile_pic'),

                        'page_url': yt_data.get('page_url'),

                        'page_description': yt_data.get('bio'),

                        'page_address': yt_data.get('country'),

                        'page_join_date': yt_data.get('join_date'),

                        'page_videos_count': yt_data.get('videos_count'),

                        'page_total_views': yt_data.get('total_views'),

                        'page_website': yt_data.get('page_website'),

                        'platform': 'youtube'

                    }

                    filtered_data = {k: v for k, v in filtered_data.items() if k in allowed_fields}

                    PageInfo.objects.create(page_group=group, **filtered_data)

                else:

                    form.add_error(None, "❌ ไม่สามารถดึงข้อมูล YouTube ได้ กรุณาตรวจสอบ URL หรือรอสักครู่")

                    return render(request, 'PageInfo/add_page.html', {'form': form, 'group': group})

            return redirect('group_detail', group_id=group.id)


    else:
        form = PageURLForm()

    return render(request, 'PageInfo/add_page.html', {'form': form, 'group': group})




def create_group(request):
    if request.method == 'POST':
        form = PageGroupForm(request.POST)
        if form.is_valid():
            page_group = form.save()
            return redirect('group_detail', group_id=page_group.id)
    else:
        form = PageGroupForm()
    return render(request, 'PageInfo/create_group.html', {'form': form})

def group_detail(request, group_id):
    group = get_object_or_404(PageGroup, id=group_id)
    pages = group.pages.all().order_by('-page_followers_count')
    posts = FacebookPost.objects.filter(page__in=pages)

    colors = ['#e20414', '#2e3d93', '#fbd305', '#355e73', '#0c733c', '#c94087']

    # 📊 Followers Chart & Interaction Pie Chart
    chart_data = []
    interaction_data = []
    total_interactions = sum(int(str(p.page_talking_count or '0').replace(',', '')) for p in pages)

    for i, page in enumerate(pages):
        interaction = int(str(page.page_talking_count or '0').replace(',', ''))
        interaction_data.append({
            'id': page.id,
            'name': page.page_name or page.page_username or 'Unnamed',
            'interactions': interaction,
            'percent': round((interaction / total_interactions * 100) if total_interactions else 0, 1),
            'color': colors[i % len(colors)]
        })
        chart_data.append({
            'id': page.id,
            'name': page.page_name or page.page_username or 'Unnamed',
            'followers': page.page_followers_count or 0,
            'profile_pic': page.profile_pic or '',
            'platform': page.platform or 'facebook',
            'color': colors[i % len(colors)]
        })

    # 🔁 followers_posts_map เพื่อ popup โพสต์ของแต่ละเพจ
    followers_posts_map = defaultdict(list)
    for post in posts:
        if not post.page:
            continue
        followers_posts_map[str(post.page.id)].append({
            'post_id': post.post_id,
            'post_content': post.post_content,
            'post_imgs': post.post_imgs,
            'post_timestamp': post.post_timestamp_dt.strftime('%Y-%m-%d %H:%M') if post.post_timestamp_dt else '',
            'reactions': post.reactions or {},
            'comment_count': post.comment_count,
            'share_count': post.share_count,
            'total_engagement': (
                    (sum(post.reactions.values()) if isinstance(post.reactions, dict) else 0) +
                    (post.comment_count or 0) +
                    (post.share_count or 0)
            ),
            'page': {
                'page_name': post.page.page_name,
                'profile_pic': post.page.profile_pic,
            }
        })

    # 📅 Number of posts by weekday (Bar Chart)
    day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    day_counts = Counter(post.post_timestamp_dt.weekday() for post in posts if post.post_timestamp_dt)
    bar_day_labels = day_labels
    bar_day_values = [day_counts.get(i, 0) for i in range(7)]
    bar_day_colors = [colors[i % len(colors)] for i in range(7)]
    posts_grouped_by_day = defaultdict(list)
    for post in posts:
        if post.post_timestamp_dt:
            weekday = post.post_timestamp_dt.weekday()
            posts_grouped_by_day[str(weekday)].append({
                'post_id': post.post_id,
                'post_content': post.post_content,
                'post_imgs': post.post_imgs,
                'post_timestamp': post.post_timestamp_dt.strftime('%Y-%m-%d %H:%M'),
                'reactions': post.reactions or {},
                'comment_count': post.comment_count,
                'share_count': post.share_count,
                'total_engagement': (sum(post.reactions.values()) if isinstance(post.reactions,
                                                                                dict) else 0) + post.comment_count + post.share_count,
                'page_name': post.page.page_name if post.page else '',
                'profile_pic': post.page.profile_pic if post.page else '',
            })

    # 🕒 Best Times To Post (Bubble Chart)
    bubble_grouped = defaultdict(list)
    posts_grouped_by_time = defaultdict(list)

    for post in posts:
        if not post.post_timestamp_dt:
            continue

        weekday = post.post_timestamp_dt.weekday()
        hour = post.post_timestamp_dt.hour
        hour_slot = (hour // 2) * 2
        key = f"{weekday}_{hour_slot}"

        bubble_grouped[key].append(post)

    bubble_data = []
    for key, grouped_posts in bubble_grouped.items():
        weekday, hour_slot = map(int, key.split('_'))
        count = len(grouped_posts)
        total_likes = sum(p.reactions.get('ถูกใจ', 0) if isinstance(p.reactions, dict) else 0 for p in grouped_posts)
        total_comments = sum(p.comment_count or 0 for p in grouped_posts)
        total_shares = sum(p.share_count or 0 for p in grouped_posts)

        bubble_data.append({
            'x': weekday,
            'y': hour_slot,
            'r': max(5, min(20, int(count ** 1.1))),
            'count': count,
            'likes': total_likes,
            'comments': total_comments,
            'shares': total_shares,
            'tooltip_label': f"{day_labels[weekday]} {hour_slot:02d}:00 - {hour_slot + 2:02d}:00",
            # Ensure tooltip label
            'key': key  # Ensure the key is present for JS
        })

        for p in grouped_posts:
            total_engagement = (
                (sum(p.reactions.values()) if isinstance(p.reactions, dict) else 0) +
                (p.comment_count or 0) +
                (p.share_count or 0)
            )
            posts_grouped_by_time[f"{weekday}_{hour_slot}"].append({
                'post_id': p.post_id,
                'post_content': p.post_content,
                'post_imgs': p.post_imgs,
                'post_timestamp': p.post_timestamp_dt.strftime('%Y-%m-%d %H:%M'),
                'reactions': p.reactions or {},
                'comment_count': p.comment_count,
                'share_count': p.share_count,
                'total_engagement': (sum(p.reactions.values()) if isinstance(p.reactions, dict) else 0) + (
                            p.comment_count or 0) + (p.share_count or 0),
                'page': {
                    'page_name': p.page.page_name if p.page else '',
                    'profile_pic': p.page.profile_pic if p.page else ''
                }
            })

    return render(request, 'PageInfo/group_detail.html', {
        'group': group,
        'pages': pages,
        'chart_data_json': json.dumps(chart_data),
        'interaction_data_json': json.dumps(interaction_data),
        'bar_day_labels': json.dumps(bar_day_labels),
        'bar_day_values': json.dumps(bar_day_values),
        'bar_day_colors': json.dumps(bar_day_colors),
        'bubble_data': json.dumps(bubble_data),
        'posts_grouped_json': json.dumps(posts_grouped_by_time),
        'posts_by_day_json': json.dumps(posts_grouped_by_day),
        'followers_posts_map': json.dumps(followers_posts_map),
    })




def index(request):
    page_groups = PageGroup.objects.prefetch_related('pages')
    total_groups = page_groups.count()  # นับจำนวนกลุ่มทั้งหมด
    return render(request, 'PageInfo/index.html', {
        'page_groups': page_groups,
        'total_groups': total_groups,  # ส่งจำนวนทั้งหมดไป template
    })

def sidebar_context(request):
    page_groups = PageGroup.objects.all()
    return {'page_groups_sidebar': page_groups, 'page_groups_count': page_groups.count()}

def pageview(request, page_id):
    page = get_object_or_404(PageInfo, id=page_id)

    facebook_posts = None
    facebook_posts_top10 = None
    facebook_posts_flop10 = None
    scatter_data = []  # ✅ เตรียม scatter_data นอก loop ใหญ่
    posts_by_day_data = []  # ✅ เตรียม posts_by_day_data

    if page.platform == "facebook":
        facebook_posts = FacebookPost.objects.filter(page=page).order_by('-post_timestamp_dt')
        posts_by_day_json = defaultdict(list)
        posts_grouped_by_time = defaultdict(list)
        heatmap_counter = {}  # ✅ สำหรับรวมข้อมูล bubble chart
        best_times_bubble = []  # ✅ สำหรับแสดงผล chart
        hour_bins = list(range(0, 24, 2))  # 0,2,4,...22

        for post in facebook_posts:
            if not post.post_timestamp_dt:
                continue

            weekday_index = post.post_timestamp_dt.weekday()
            hour = post.post_timestamp_dt.hour
            hour_slot = (hour // 2) * 2  # เช่น 13 => 12
            key = f"{weekday_index}_{hour_slot}"

            # ✅ แปลง reactions
            reactions = post.reactions or {}
            if isinstance(reactions, str):
                try:
                    reactions = json.loads(reactions)
                except json.JSONDecodeError:
                    reactions = {}

            # ✅ คำนวณ metrics
            post.like_count = reactions.get("ถูกใจ", 0)
            post.comment_count = post.comment_count or 0
            post.share_count = post.share_count or 0
            post.total_engagement = sum(reactions.values()) + post.comment_count + post.share_count

            post.reach = getattr(post, 'reach_per_post', None)
            post.impressions = getattr(post, 'impressions', None)

            if post.reach and isinstance(post.reach, (int, float)) and post.reach > 0:
                post.interaction_rate = f"{post.total_engagement / post.reach:.4%}"
            else:
                post.interaction_rate = "0%"
                post.reach = "-"

            if post.impressions and isinstance(post.impressions, (int, float)) and post.impressions > 0:
                post.impression_per_view = f"{post.total_engagement / post.impressions:.4f}"
            else:
                post.impression_per_view = "-"

            post.negative_sentiment_share = "0%"

            # ✅ เพิ่มข้อมูลเข้า posts_by_day_json
            posts_by_day_json[str(weekday_index)].append({
                "post_id": post.post_id,
                "post_imgs": post.post_imgs,
                "post_content": post.post_content,
                "post_timestamp": post.post_timestamp_text,
                "profile_pic": post.page.profile_pic if post.page else None,
                "page_name": post.page.page_name if post.page else None,
                "comment_count": post.comment_count,
                "share_count": post.share_count,
                "total_engagement": post.total_engagement,
                "reactions": reactions,
            })

            # ✅ เพิ่มข้อมูลเข้า posts_grouped_by_time สำหรับ popup bubble chart
            posts_grouped_by_time[key].append({
                "post_id": post.post_id,
                "post_content": post.post_content,
                "post_imgs": post.post_imgs,
                "post_timestamp": post.post_timestamp_text,
                "reactions": reactions,
                "comment_count": post.comment_count,
                "share_count": post.share_count,
                "total_engagement": post.total_engagement,
                "page": {
                    "page_name": post.page.page_name if post.page else '',
                    "profile_pic": post.page.profile_pic if post.page else ''
                }
            })

            # ✅ เพิ่มข้อมูลเข้า scatter chart
            scatter_data.append({
                "x": post.post_timestamp_dt.strftime("%Y-%m-%d"),
                "y": post.total_engagement,
                "content": (post.post_content[:30] + '...') if post.post_content else "",
                "page_name": page.page_name,
                "timestamp_text": post.post_timestamp_text,
                "img": post.post_imgs[0] if post.post_imgs else None,
            })

            # ✅ รวมข้อมูล bubble chart
            if key not in heatmap_counter:
                heatmap_counter[key] = {
                    "count": 0,
                    "likes": 0,
                    "comments": 0,
                    "shares": 0,
                }

            heatmap_counter[key]["count"] += 1
            heatmap_counter[key]["likes"] += reactions.get("ถูกใจ", 0)
            heatmap_counter[key]["comments"] += post.comment_count
            heatmap_counter[key]["shares"] += post.share_count

        # ✅ ฟังก์ชันกำหนดสีแยกตามจำนวนโพสต์
        def get_color_by_count(count):
            color_map = {
                1: "#cdb4db",
                2: "#c5f6f7",
                3: "#f9c6c9",
                4: "#ffd6a5",
                5: "#FF6962",
            }
            return color_map.get(count, "#9E9E9E")

        # ✅ แปลง heatmap_counter => best_times_bubble
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for key, val in heatmap_counter.items():
            weekday, hour = map(int, key.split("_"))
            label = f"{day_order[weekday]} {hour:02d}:00 - {hour + 2:02d}:00"
            best_times_bubble.append({
                "x": weekday,
                "y": hour,
                "r": max(4, min(20, val["count"] * 3)),
                "count": val["count"],
                "likes": val["likes"],
                "comments": val["comments"],
                "shares": val["shares"],
                "label": label,
                "key": key,
                "color": get_color_by_count(val["count"]),
            })

        facebook_posts_top10 = sorted(facebook_posts, key=lambda p: p.total_engagement, reverse=True)[:10]
        facebook_posts_flop10 = sorted(facebook_posts, key=lambda p: p.total_engagement)[:10]
        # ===== หลังจากสร้าง facebook_posts สำเร็จแล้ว
        top_hashtags_raw = extract_top_hashtags(facebook_posts)  # ดึง (tag, count)
        top_count_max = top_hashtags_raw[0][1] if top_hashtags_raw else 1

        # เตรียมข้อมูลสำหรับ render
        top_hashtags = []
        for tag, count in top_hashtags_raw:
            font_size = round(0.8 + (count / top_count_max) * 1.5, 2)
            color_hue = round(120 - (count / top_count_max) * 60, 2)
            top_hashtags.append({
                "tag": tag,
                "count": count,
                "font_size": font_size,
                "color_hue": color_hue,
            })

        # ✅ สร้างข้อมูล follower line chart จากตาราง FollowerHistory
        follower_qs = FollowerHistory.objects.filter(page=page).order_by('date')
        follower_data = [
            {"date": f.date.strftime("%b %d"), "followers": f.page_followers_count}
            for f in follower_qs if f.page_followers_count
        ]

        # ✅ เตรียม Counter สำหรับนับจำนวนโพสต์ตามวันในสัปดาห์
        weekday_counter = Counter()
        for post in facebook_posts:
            if post.post_timestamp_dt:
                weekday_name = post.post_timestamp_dt.strftime('%A')
                weekday_counter[weekday_name] += 1

        # ✅ เตรียมข้อมูล posts by day chart
        posts_by_day_data = [{"day": day, "count": weekday_counter.get(day, 0)} for day in calendar.day_name]
        bar_day_labels = list(calendar.day_name)  # ["Monday", "Tuesday", ..., "Sunday"]
        bar_day_values = [weekday_counter.get(day, 0) for day in bar_day_labels]

        def get_bar_color_by_count(count):
            color_map = {
                1: "#a2d2ff",  # ฟ้าพาสเทล
                2: "#cdb4db",  # ม่วงพาสเทล
                3: "#ffd6a5",  # เหลืองพาสเทล
                4: "#ffdac1",  # ส้มพาสเทล
                5: "#f9c6c9",  # ชมพูพาสเทล
                6: "#b5ead7",  # เขียวพาสเทล
            }
            return color_map.get(count, "#e2e2e2")  # fallback สีเทา

        bar_day_colors = [get_bar_color_by_count(weekday_counter.get(day, 0)) for day in bar_day_labels]

        # ✅ เตรียมข้อมูลสำหรับ Bubble Chart Best Times to Post
        best_times_data = []
        hour_bins = list(range(0, 24, 2))  # bin ทุก 2 ชั่วโมง: 0,2,4,...22
        heatmap_counter = {}

        for post in facebook_posts:
            if post.post_timestamp_dt:
                weekday = post.post_timestamp_dt.strftime('%A')  # Monday - Sunday
                hour = post.post_timestamp_dt.hour
                time_bin = hour_bins[hour // 2]  # ex: 9 => 8
                key = (weekday, time_bin)

                # ดึง reaction แบบแยกประเภท
                reactions = post.reactions or {}
                if isinstance(reactions, str):
                    try:
                        reactions = json.loads(reactions)
                    except json.JSONDecodeError:
                        reactions = {}

                likes = reactions.get("ถูกใจ", 0)
                comments = post.comment_count or 0
                shares = post.share_count or 0

                if key not in heatmap_counter:
                    heatmap_counter[key] = {
                        "count": 0,
                        "likes": 0,
                        "comments": 0,
                        "shares": 0,
                        "engagement": 0,
                    }

                heatmap_counter[key]["count"] += 1
                heatmap_counter[key]["likes"] += likes
                heatmap_counter[key]["comments"] += comments
                heatmap_counter[key]["shares"] += shares
                heatmap_counter[key]["engagement"] += likes + comments + shares

        # ✅ แปลงข้อมูลให้พร้อมใช้ใน Chart.js
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        best_times_bubble = []


        # ฟังก์ชันเลือกสีตามจำนวนโพสต์
        def get_color_by_count(count):
            color_map = {
                1: "#cdb4db",
                2: "#c5f6f7",
                3: "#f9c6c9",
                4: "#ffd6a5",
                5: "#FF6962",
            }
            return color_map.get(count, "#9E9E9E")  # สีเทาสำหรับ fallback

        for (day, hour), val in heatmap_counter.items():
            key_str = f"{day_order.index(day)}_{hour}"  # ✅ ให้ตรงกับ key ที่ใช้ใน posts_grouped_by_time

            tooltip_label = f"{day} {hour:02d}:00 - {hour + 2:02d}:00"
            bubble = {
                "x": day_order.index(day),
                "y": hour,
                "r": max(4, min(20, val["count"] * 3)),
                "count": val["count"],
                "likes": val.get("likes", 0),
                "comments": val.get("comments", 0),
                "shares": val.get("shares", 0),
                "label": tooltip_label,  # ✅ เดิม
                "tooltip_label": tooltip_label,  # ✅ เพิ่มสำหรับ group_detail style
                "key": key_str,
                "color": get_color_by_count(val["count"]),
                "customTooltip": {
                    "line1": tooltip_label,
                    "line2": f"{val['count']} Number of posts",
                    "line3": f"{val.get('likes', 0)} Likes, {val.get('comments', 0)} Comments, {val.get('shares', 0)} Shares"
                }
            }

            best_times_bubble.append(bubble)

    return render(request, 'PageInfo/pageview.html', {
        'page': page,
        'facebook_posts': facebook_posts,
        'facebook_posts_top10': facebook_posts_top10,
        'facebook_posts_flop': facebook_posts_flop10,
        'scatter_data': scatter_data,
        'follower_data': follower_data,  # ✅ ส่งไปยังเทมเพลตด้วย
        'posts_by_day_data': posts_by_day_data,  # ✅ เพิ่มเพื่อส่งให้ Bar Chart
        # ✅ เพิ่ม 2 ตัวนี้เพื่อใช้กับ Chart.js
        'bar_day_labels': json.dumps(bar_day_labels),
        'bar_day_values': json.dumps(bar_day_values),
        'bubble_data': json.dumps(best_times_bubble),
        'bar_day_colors': json.dumps(bar_day_colors),
        'top_hashtags': top_hashtags,
        'posts_by_day_json': json.dumps(posts_by_day_json),
        'posts_grouped_json': json.dumps(posts_grouped_by_time),
    })


