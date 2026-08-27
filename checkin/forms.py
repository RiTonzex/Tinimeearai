from django import forms
from django.core.exceptions import ValidationError
from .models import Post

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']

def validate_image_file(image):
    """
    ตรวจสอบความปลอดภัยของไฟล์รูปภาพ (ขนาดไฟล์ และนามสกุล)
    """
    if hasattr(image, 'size') and image.size > MAX_UPLOAD_SIZE:
        raise ValidationError('ขนาดไฟล์รูปภาพต้องไม่เกิน 10 MB')
    
    if hasattr(image, 'name'):
        ext = image.name.split('.')[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(f'รองรับเฉพาะไฟล์รูปภาพนามสกุล {", ".join(ALLOWED_EXTENSIONS)} เท่านั้น')
    return image

class PostForm(forms.ModelForm):
    """
    Form สำหรับสร้างโพสต์ใหม่
    """
    class Meta:
        model = Post
        fields = ['image', 'caption', 'location_name', 'latitude', 'longitude']
        widgets = {
            'image': forms.FileInput(attrs={
                'id': 'image-input',
                'accept': 'image/jpeg,image/png,image/webp',
                'class': 'hidden',
                'required': 'required'
            }),
            'caption': forms.Textarea(attrs={
                'id': 'caption-input',
                'rows': 4,
                'placeholder': 'แชร์ความประทับใจ ที่นี่มีอะไรเด็ด อาหาร บรรยากาศ หรือมุมถ่ายรูปสวยๆ...',
                'class': 'w-full px-4 py-3 text-slate-100 bg-slate-800/60 rounded-2xl border border-slate-700/80 focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none transition duration-200 resize-none text-sm md:text-base leading-relaxed',
            }),
            'location_name': forms.TextInput(attrs={
                'id': 'location-name-input',
                'placeholder': 'ระบุชื่อสถานที่ หรือกดปุ่มเช็คอินเพื่อดึงพิกัดอัตโนมัติ',
                'class': 'w-full pl-10 pr-4 py-3 text-slate-100 bg-slate-800/60 rounded-2xl border border-slate-700/80 focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none transition duration-200 text-sm md:text-base',
            }),
            'latitude': forms.HiddenInput(attrs={'id': 'latitude-input'}),
            'longitude': forms.HiddenInput(attrs={'id': 'longitude-input'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        return validate_image_file(image)

class PostEditForm(forms.ModelForm):
    """
    Form สำหรับแก้ไขโพสต์เดิม (รูปภาพไม่บังคับเลือกใหม่)
    """
    class Meta:
        model = Post
        fields = ['image', 'caption', 'location_name', 'latitude', 'longitude']
        widgets = {
            'image': forms.FileInput(attrs={
                'id': 'image-input',
                'accept': 'image/jpeg,image/png,image/webp',
                'class': 'hidden',
            }),
            'caption': forms.Textarea(attrs={
                'id': 'caption-input',
                'rows': 4,
                'class': 'w-full px-4 py-3 text-slate-100 bg-slate-800/60 rounded-2xl border border-slate-700/80 focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none transition duration-200 resize-none text-sm md:text-base leading-relaxed',
            }),
            'location_name': forms.TextInput(attrs={
                'id': 'location-name-input',
                'class': 'w-full pl-10 pr-4 py-3 text-slate-100 bg-slate-800/60 rounded-2xl border border-slate-700/80 focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none transition duration-200 text-sm md:text-base',
            }),
            'latitude': forms.HiddenInput(attrs={'id': 'latitude-input'}),
            'longitude': forms.HiddenInput(attrs={'id': 'longitude-input'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            return validate_image_file(image)
        return image
