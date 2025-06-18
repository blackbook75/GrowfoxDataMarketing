from django.db import models

class PageGroup(models.Model):
    group_name = models.CharField(max_length=255, default='Unnamed Group')

    def __str__(self):
        return self.group_name


class PageInfo(models.Model):
    page_group = models.ForeignKey(PageGroup, on_delete=models.CASCADE, related_name='pages')
    # ข้อมูลทั่วไป

    platform = models.CharField(
        max_length=20,
        choices=[('facebook', 'Facebook'), ('tiktok', 'TikTok'), ('instagram', 'Instagram'),  ('lemon8', 'Lemon8'),  ('youtube', 'Youtube')],
        default='facebook'
    )
    page_name = models.CharField(max_length=255, null=True, blank=True)
    page_url = models.URLField(max_length=500, null=True, blank=True)
    profile_pic = models.URLField(max_length=500, null=True, blank=True)
    page_username = models.CharField(max_length=255, null=True, blank=True)
    page_id = models.CharField(max_length=100, null=True, blank=True)
    is_business_page = models.BooleanField(null=True, blank=True)


    # Meta HTML
    page_followers = models.CharField(max_length=100, null=True, blank=True)
    page_likes = models.CharField(max_length=100, null=True, blank=True)
    page_followers_count = models.IntegerField(null=True, blank=True)
    page_likes_count = models.CharField(max_length=100, null=True, blank=True)
    page_talking_count = models.CharField(max_length=100, null=True, blank=True)
    page_were_here_count = models.CharField(max_length=100, null=True, blank=True)
    page_description = models.TextField(null=True, blank=True)
    page_category = models.CharField(max_length=255, null=True, blank=True)
    page_address = models.CharField(max_length=500, null=True, blank=True)
    page_phone = models.CharField(max_length=100, null=True, blank=True)
    page_email = models.EmailField(max_length=254, null=True, blank=True)
    page_website = models.URLField(max_length=500, null=True, blank=True)


    def __str__(self):
        return self.page_name or "Unnamed Page"
    following_count = models.CharField(max_length=100, null=True, blank=True)  # เช่น "9"
    age = models.CharField(max_length=50, null=True, blank=True)  # เช่น "ช่วงอายุ 20 ปี"
    # 🔥 เพิ่ม field สำหรับ Instagram post_count
    post_count = models.IntegerField(null=True, blank=True)
    page_join_date = models.CharField(max_length=100, null=True, blank=True)
    page_videos_count = models.BigIntegerField(null=True, blank=True)
    page_total_views = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return self.page_name or "Unnamed Page"

class FacebookPost(models.Model):
    page = models.ForeignKey(PageInfo, on_delete=models.CASCADE, related_name='facebook_posts')
    post_id = models.CharField(max_length=100, unique=True)
    post_timestamp_dt = models.DateTimeField()
    post_timestamp_text = models.TextField()
    post_content = models.TextField()
    post_imgs = models.JSONField(blank=True, null=True, default=list)
    reactions = models.JSONField(blank=True, null=True, default=dict)
    comment_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.page.page_name} - {self.post_timestamp_text}"

class FollowerHistory(models.Model):
    page = models.ForeignKey(PageInfo, on_delete=models.CASCADE)
    date = models.DateField()
    page_followers_count = models.IntegerField(null=True, blank=True)  # ✅ ชื่อนี้

    def __str__(self):
        return f"{self.page.page_name} - {self.date} - {self.page_followers_count}"