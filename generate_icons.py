from PIL import Image, ImageDraw, ImageFont
import os

# الأحجام المطلوبة للأيقونات
SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

def create_base_icon(size=512):
    # إنشاء صورة جديدة بخلفية خضراء
    img = Image.new('RGB', (size, size), '#28a745')
    draw = ImageDraw.Draw(img)
    
    # رسم دائرة بيضاء في المنتصف
    margin = size // 4
    draw.ellipse([margin, margin, size-margin, size-margin], fill='white')
    
    # حفظ الأيقونة الأساسية
    base_icon_path = f'static/icons/icon-{size}x{size}.png'
    img.save(base_icon_path, 'PNG', quality=95)
    return base_icon_path

def generate_icons():
    # إنشاء الأيقونة الأساسية
    base_icon_path = create_base_icon(512)
    
    # فتح الصورة الأصلية
    img = Image.open(base_icon_path)
    
    # إنشاء الأيقونات بجميع الأحجام
    for size in SIZES:
        if size == 512:  # تخطي الحجم 512 لأنه تم إنشاؤه بالفعل
            continue
        output_path = f'static/icons/icon-{size}x{size}.png'
        # تغيير حجم الصورة مع الحفاظ على الجودة
        resized_img = img.resize((size, size), Image.LANCZOS)
        resized_img.save(output_path, 'PNG', quality=95)
        print(f'تم إنشاء أيقونة بحجم {size}x{size}')

if __name__ == '__main__':
    # التأكد من وجود مجلد الأيقونات
    if not os.path.exists('static/icons'):
        os.makedirs('static/icons')
    generate_icons()
