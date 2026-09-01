from django import forms
from django.core.exceptions import ValidationError
from .models import Post, Comment

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB per image
ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']

def validate_image_file(image):
    """
    ตรวจสอบความปลอดภัยของไฟล์รูปภาพ (ขนาดไฟล์ และนามสกุล)
    """
    if hasattr(image, 'size') and image.size > MAX_UPLOAD_SIZE:
        raise ValidationError('ขนาดไฟล์รูปภาพต้องไม่เกิน 10 MB ต่อรูป')
    
    if hasattr(image, 'name'):
        ext = image.name.split('.')[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(f'รองรับเฉพาะไฟล์รูปภาพนามสกุล {", ".join(ALLOWED_EXTENSIONS)} เท่านั้น')
    return image

class PostForm(forms.ModelForm):
    """
    Form สำหรับสร้างโพสต์ใหม่ (รองรับหลายรูปภาพ Multi-upload)
    """
    class Meta:
        model = Post
        fields = ['image', 'caption', 'tags', 'location_name', 'latitude', 'longitude']
        widgets = {
            'image': forms.FileInput(attrs={
                'id': 'image-input',
                'accept': 'image/jpeg,image/png,image/webp',
                'class': 'hidden',
            }),
            'caption': forms.Textarea(attrs={
                'id': 'caption-input',
                'rows': 4,
                'placeholder': 'แชร์ความประทับใจ ที่นี่มีอะไรเด็ด อาหาร บรรยากาศ หรือมุมถ่ายรูปสวยๆ...',
                'class': 'w-full px-4 py-3 text-white bg-zinc-900 rounded-2xl border border-zinc-800 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none transition duration-200 resize-none text-sm md:text-base leading-relaxed',
            }),
            'tags': forms.TextInput(attrs={
                'id': 'tags-input',
                'placeholder': 'เช่น จุดชมวิว, คาเฟ่, ธรรมชาติ, ถ่ายรูปสวย',
                'class': 'w-full pl-10 pr-4 py-3 text-white bg-zinc-900 rounded-2xl border border-zinc-800 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none transition duration-200 text-sm md:text-base',
            }),
            'location_name': forms.TextInput(attrs={
                'id': 'location-name-input',
                'placeholder': 'ระบุชื่อสถานที่ หรือกดปุ่มเช็คอินเพื่อดึงพิกัดอัตโนมัติ',
                'class': 'w-full pl-10 pr-4 py-3 text-white bg-zinc-900 rounded-2xl border border-zinc-800 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none transition duration-200 text-sm md:text-base',
            }),
            'latitude': forms.HiddenInput(attrs={'id': 'latitude-input'}),
            'longitude': forms.HiddenInput(attrs={'id': 'longitude-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].required = False

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            return validate_image_file(image)
        return image

class PostEditForm(forms.ModelForm):
    """
    Form สำหรับแก้ไขโพสต์เดิม
    """
    class Meta:
        model = Post
        fields = ['image', 'caption', 'tags', 'location_name', 'latitude', 'longitude']
        widgets = {
            'image': forms.FileInput(attrs={
                'id': 'image-input',
                'accept': 'image/jpeg,image/png,image/webp',
                'class': 'hidden',
            }),
            'caption': forms.Textarea(attrs={
                'id': 'caption-input',
                'rows': 4,
                'class': 'w-full px-4 py-3 text-white bg-zinc-900 rounded-2xl border border-zinc-800 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none transition duration-200 resize-none text-sm md:text-base leading-relaxed',
            }),
            'tags': forms.TextInput(attrs={
                'id': 'tags-input',
                'placeholder': 'เช่น จุดชมวิว, คาเฟ่, ธรรมชาติ',
                'class': 'w-full pl-10 pr-4 py-3 text-white bg-zinc-900 rounded-2xl border border-zinc-800 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none transition duration-200 text-sm md:text-base',
            }),
            'location_name': forms.TextInput(attrs={
                'id': 'location-name-input',
                'class': 'w-full pl-10 pr-4 py-3 text-white bg-zinc-900 rounded-2xl border border-zinc-800 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none transition duration-200 text-sm md:text-base',
            }),
            'latitude': forms.HiddenInput(attrs={'id': 'latitude-input'}),
            'longitude': forms.HiddenInput(attrs={'id': 'longitude-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].required = False

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            return validate_image_file(image)
        return image

class CommentForm(forms.ModelForm):
    """
    Form สำหรับเขียนความคิดเห็นในโพสต์
    """
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={
                'id': 'comment-input',
                'placeholder': 'เขียนความคิดเห็น...',
                'class': 'w-full px-4 py-3.5 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-xs md:text-sm transition',
                'autocomplete': 'off',
                'required': 'required'
            })
        }

class ThaiUserCreationForm(forms.ModelForm):
    """
    ฟอร์มสมัครสมาชิกพร้อมข้อความแจ้งเตือนภาษาไทยครบถ้วน
    """
    username = forms.CharField(
        label="ชื่อผู้ใช้",
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'ระบุชื่อผู้ใช้งาน (เช่น traveler_demo)',
            'class': 'w-full px-4 py-3.5 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-sm transition shadow-inner'
        })
    )
    password = forms.CharField(
        label="รหัสผ่าน",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'ระบุรหัสผ่าน (อย่างน้อย 8 ตัวอักษร)',
            'class': 'w-full px-4 py-3.5 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-sm transition shadow-inner'
        })
    )
    password_confirm = forms.CharField(
        label="ยืนยันรหัสผ่าน",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'ระบุรหัสผ่านเดิมอีกครั้งเพื่อยืนยัน',
            'class': 'w-full px-4 py-3.5 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-sm transition shadow-inner'
        })
    )

    class Meta:
        model = Post._meta.get_field('user').remote_field.model
        fields = ('username',)

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise ValidationError('กรุณาระบุชื่อผู้ใช้งาน')
        
        UserModel = Post._meta.get_field('user').remote_field.model
        if UserModel.objects.filter(username__iexact=username).exists():
            raise ValidationError('ชื่อผู้ใช้นี้ถูกใช้งานแล้ว กรุณาเลือกชื่อผู้ใช้อื่น')
        
        import re
        if not re.match(r'^[\w.@+-]+$', username):
            raise ValidationError('ชื่อผู้ใช้ต้องประกอบด้วยตัวอักษร ตัวเลข และเครื่องหมาย @/./+/-/_ เท่านั้น')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if not password:
            raise ValidationError('กรุณาระบุรหัสผ่าน')
        
        if len(password) < 8:
            raise ValidationError('รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร')
        
        if password.isdigit():
            raise ValidationError('รหัสผ่านต้องไม่เป็นตัวเลขเพียงอย่างเดียว (ต้องมีตัวอักษรผสมด้วย)')
        
        common_passwords = ['12345678', 'password', 'password123', 'admin123', 'qwertyuiop', '11111111', '00000000', '123456789']
        if password.lower() in common_passwords:
            raise ValidationError('รหัสผ่านนี้ง่ายเกินไป กรุณาตั้งรหัสผ่านที่มีความปลอดภัยมากกว่านี้')

        return password

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and username and password.lower() == username.lower():
            self.add_error('password', 'รหัสผ่านต้องไม่ตรงกับชื่อผู้ใช้')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'รหัสผ่านและยืนยันรหัสผ่านไม่ตรงกัน กรุณาตรวจสอบอีกครั้ง')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.Form):
    """
    ฟอร์มสำหรับอัปเดตข้อมูลส่วนตัวในหน้าตั้งค่า
    """
    avatar = forms.ImageField(
        label="รูปโปรไฟล์",
        required=False,
        widget=forms.FileInput(attrs={
            'accept': 'image/*',
            'id': 'avatar-file-input',
            'class': 'hidden'
        })
    )
    display_name = forms.CharField(
        label="ชื่อที่แสดง (Display Name)",
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'เช่น บอล สายลุย, ต๊ะ พิกัดลับ (ชื่อที่คนอื่นจะเห็น)',
            'class': 'w-full px-4 py-3.5 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-xs md:text-sm transition shadow-inner font-semibold'
        })
    )
    bio = forms.CharField(
        label="ประวัติโดยย่อ (Bio)",
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'แนะนำตัวสั้นๆ สไตล์การท่องเที่ยว คำคม หรือพิกัดโปรด...',
            'class': 'w-full px-4 py-3 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-xs md:text-sm transition shadow-inner resize-none leading-relaxed'
        })
    )
    first_name = forms.CharField(
        label="ชื่อจริง",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'ชื่อของคุณ',
            'class': 'w-full px-4 py-3 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-xs md:text-sm transition shadow-inner'
        })
    )
    last_name = forms.CharField(
        label="นามสกุล",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'นามสกุล',
            'class': 'w-full px-4 py-3 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-xs md:text-sm transition shadow-inner'
        })
    )
    email = forms.EmailField(
        label="อีเมล",
        required=False,
        widget=forms.EmailInput(attrs={
            'placeholder': 'you@example.com',
            'class': 'w-full px-4 py-3 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-xs md:text-sm transition shadow-inner'
        })
    )


class ThaiPasswordChangeForm(forms.Form):
    """
    ฟอร์มเปลี่ยนรหัสผ่านในหน้าตั้งค่า พร้อมข้อความภาษาไทย
    """
    old_password = forms.CharField(
        label="รหัสผ่านปัจจุบัน",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'ระบุรหัสผ่านเดิม',
            'class': 'w-full px-4 py-3.5 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-xs md:text-sm transition shadow-inner'
        })
    )
    new_password1 = forms.CharField(
        label="รหัสผ่านใหม่",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'รหัสผ่านใหม่ (อย่างน้อย 8 ตัวอักษร)',
            'class': 'w-full px-4 py-3.5 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-xs md:text-sm transition shadow-inner'
        })
    )
    new_password2 = forms.CharField(
        label="ยืนยันรหัสผ่านใหม่",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'ระบุรหัสผ่านใหม่อีกครั้ง',
            'class': 'w-full px-4 py-3.5 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-xs md:text-sm transition shadow-inner'
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise ValidationError('รหัสผ่านปัจจุบันไม่ถูกต้อง')
        return old_password

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1', '')
        if len(password) < 8:
            raise ValidationError('รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 8 ตัวอักษร')
        if password.isdigit():
            raise ValidationError('รหัสผ่านต้องไม่เป็นตัวเลขเพียงอย่างเดียว')
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            self.add_error('new_password2', 'รหัสผ่านใหม่ทั้ง 2 ช่องไม่ตรงกัน')
        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data['new_password1'])
        self.user.save()
        return self.user


class ForgotPasswordRequestForm(forms.Form):
    """
    ฟอร์มขอรับรหัส OTP สำหรับรีเซ็ตรหัสผ่าน (ระบุ Username หรือ Email)
    """
    identifier = forms.CharField(
        label="ชื่อผู้ใช้งาน หรือ อีเมล",
        widget=forms.TextInput(attrs={
            'placeholder': 'ระบุชื่อผู้ใช้งาน หรือ อีเมลที่ผูกไว้กับบัญชี',
            'class': 'w-full px-4 py-3.5 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-xs md:text-sm transition shadow-inner font-medium',
            'autofocus': 'autofocus'
        })
    )

    def clean_identifier(self):
        from django.contrib.auth.models import User
        ident = self.cleaned_data.get('identifier', '').strip()
        if not ident:
            raise ValidationError('กรุณาระบุชื่อผู้ใช้งานหรืออีเมล')
        
        user = None
        if '@' in ident:
            user = User.objects.filter(email__iexact=ident).first()
        if not user:
            user = User.objects.filter(username__iexact=ident).first()

        if not user:
            raise ValidationError('ไม่พบบัญชีผู้ใช้งานที่ตรงกับข้อมูลที่ระบุ')

        if not user.email or not user.email.strip():
            raise ValidationError('บัญชีนี้ยังไม่ได้ระบุอีเมลในระบบ จึงไม่สามารถส่งรหัสรีเซ็ตรหัสผ่านได้ กรุณาติดต่อผู้ดูแลระบบ')

        self.user = user
        return ident


class VerifyOTPOnlyForm(forms.Form):
    """
    ฟอร์มขั้นตอนที่ 2: กรอกและตรวจสอบรหัส OTP 6 หลัก
    """
    otp_code = forms.CharField(
        label="รหัสยืนยัน 6 หลัก (OTP)",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': '••••••',
            'class': 'w-full px-4 py-4 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-600 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-center font-mono text-2xl tracking-[0.5em] transition shadow-inner font-black',
            'maxlength': '6',
            'autocomplete': 'one-time-code',
            'autofocus': 'autofocus'
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_otp_code(self):
        from .models import PasswordResetOTP
        code = self.cleaned_data.get('otp_code', '').strip()
        if len(code) != 6 or not code.isdigit():
            raise ValidationError('รหัส OTP ต้องเป็นตัวเลข 6 หลัก')

        latest_otp = PasswordResetOTP.objects.filter(
            user=self.user,
            is_used=False
        ).order_by('-created_at').first()

        if not latest_otp:
            raise ValidationError('ไม่พบรหัสยืนยัน OTP สำหรับบัญชีนี้ กรุณากดขอรหัสใหม่')

        if latest_otp.attempts >= 5:
            raise ValidationError('คุณกรอกรหัส OTP ผิดเกิน 5 ครั้ง รหัสนี้ถูกยกเลิกเพื่อความปลอดภัย กรุณากดขอรหัสใหม่อีกครั้ง')

        if not latest_otp.is_valid():
            raise ValidationError('รหัสยืนยัน OTP หมดอายุแล้ว กรุณากดขอรหัสใหม่')

        if latest_otp.otp_code != code:
            latest_otp.attempts += 1
            latest_otp.save(update_fields=['attempts'])
            remaining_attempts = max(0, 5 - latest_otp.attempts)
            if remaining_attempts > 0:
                raise ValidationError(f'รหัสยืนยัน OTP ไม่ถูกต้อง (เหลือโอกาสกรอกอีก {remaining_attempts} ครั้ง)')
            else:
                raise ValidationError('คุณกรอกรหัส OTP ผิดครบ 5 ครั้งแล้ว รหัสถูกยกเลิก กรุณาขอรหัสใหม่')

        self.otp_record = latest_otp
        return code



class SetNewPasswordForm(forms.Form):
    """
    ฟอร์มขั้นตอนที่ 3: กำหนดรหัสผ่านใหม่ (หลังจากยืนยัน OTP สำเร็จแล้วเท่านั้น)
    """
    new_password1 = forms.CharField(
        label="รหัสผ่านใหม่",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'รหัสผ่านใหม่ (อย่างน้อย 8 ตัวอักษร)',
            'class': 'w-full px-4 py-3.5 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-xs md:text-sm transition shadow-inner',
            'autofocus': 'autofocus'
        })
    )
    new_password2 = forms.CharField(
        label="ยืนยันรหัสผ่านใหม่",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'ระบุรหัสผ่านใหม่อีกครั้ง',
            'class': 'w-full px-4 py-3.5 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-white/30 focus:border-zinc-700 outline-none text-xs md:text-sm transition shadow-inner'
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1', '')
        if len(password) < 8:
            raise ValidationError('รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 8 ตัวอักษร')
        if password.isdigit():
            raise ValidationError('รหัสผ่านต้องไม่เป็นตัวเลขเพียงอย่างเดียว')
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            self.add_error('new_password2', 'รหัสผ่านใหม่ทั้ง 2 ช่องไม่ตรงกัน')
        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data['new_password1'])
        self.user.save()
        return self.user



class DeleteAccountForm(forms.Form):
    """
    ฟอร์มสำหรับยืนยันการลบบัญชีผู้ใช้ตนเองถาวร (Danger Zone)
    """
    password = forms.CharField(
        label="รหัสผ่านปัจจุบัน",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'ระบุรหัสผ่านของคุณเพื่อยืนยัน',
            'class': 'w-full px-4 py-3.5 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-rose-500/40 focus:border-rose-700 outline-none text-xs md:text-sm transition shadow-inner font-medium'
        })
    )
    confirmation_text = forms.CharField(
        label="พิมพ์คำว่า 'ลบบัญชี'",
        widget=forms.TextInput(attrs={
            'placeholder': "พิมพ์คำว่า 'ลบบัญชี' เพื่อยืนยัน",
            'class': 'w-full px-4 py-3.5 rounded-2xl bg-zinc-900 border border-zinc-800 text-white placeholder-zinc-500 focus:ring-2 focus:ring-rose-500/40 focus:border-rose-700 outline-none text-xs md:text-sm transition shadow-inner font-bold'
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not self.user.check_password(password):
            raise ValidationError('รหัสผ่านปัจจุบันไม่ถูกต้อง')
        return password

    def clean_confirmation_text(self):
        text = self.cleaned_data.get('confirmation_text', '').strip()
        if text not in ('ลบบัญชี', 'DELETE', 'delete'):
            raise ValidationError("กรุณาพิมพ์คำว่า 'ลบบัญชี' ให้ถูกต้องเพื่อยืนยัน")
        return text

