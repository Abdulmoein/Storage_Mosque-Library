from flask import Flask, render_template, request, redirect, url_for, flash, send_file, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from io import BytesIO

# تسجيل الخط العربي
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Noto_Naskh_Arabic', 'static', 'NotoNaskhArabic-Regular.ttf')
pdfmetrics.registerFont(TTFont('NotoNaskhArabic', FONT_PATH))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    size = db.Column(db.String(20), nullable=False)
    riwaya = db.Column(db.String(100))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    books = Book.query.all()
    return render_template('index.html', books=books)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('خطأ في اسم المستخدم أو كلمة المرور')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    if request.method == 'POST':
        book = Book(
            title=request.form.get('title'),
            category=request.form.get('category'),
            quantity=int(request.form.get('quantity')),
            size=request.form.get('size'),
            riwaya=request.form.get('riwaya')
        )
        db.session.add(book)
        db.session.commit()
        flash('تمت إضافة الكتاب بنجاح')
        return redirect(url_for('index'))
    return render_template('add_book.html')

@app.route('/update_quantity/<int:id>', methods=['POST'])
@login_required
def update_quantity(id):
    book = Book.query.get_or_404(id)
    action = request.form.get('action')
    if action == 'increase':
        book.quantity += 1
    elif action == 'decrease' and book.quantity > 0:
        book.quantity -= 1
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit_book/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_book(id):
    book = Book.query.get_or_404(id)
    if request.method == 'POST':
        book.title = request.form['title']
        book.category = request.form['category']
        book.size = request.form['size']
        book.quantity = int(request.form['quantity'])
        book.riwaya = request.form['riwaya']
        
        db.session.commit()
        flash('تم تعديل الكتاب بنجاح', 'success')
        return redirect(url_for('index'))
    
    return render_template('edit_book.html', book=book)

@app.route('/delete_book/<int:id>')
@login_required
def delete_book(id):
    book = Book.query.get_or_404(id)
    db.session.delete(book)
    db.session.commit()
    flash('تم حذف الكتاب بنجاح', 'success')
    return redirect(url_for('index'))

@app.route('/generate_report')
@login_required
def generate_report():
    books = Book.query.all()

    # تجهيز البيانات للتقرير
    categories = {}
    total_books = 0
    for book in books:
        if book.category not in categories:
            categories[book.category] = {'count': 0, 'books': []}
        categories[book.category]['count'] += book.quantity
        categories[book.category]['books'].append(book)
        total_books += book.quantity

    # إنشاء ملف PDF
    pdf_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'report.pdf')
    doc = SimpleDocTemplate(pdf_file, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    # تعريف نمط النص
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Normal'],
        fontName='NotoNaskhArabic',
        fontSize=16,
        leading=20,
        alignment=1,  # وسط
        spaceAfter=20,
    )
    
    normal_style = ParagraphStyle(
        name='NormalStyle',
        parent=styles['Normal'],
        fontName='NotoNaskhArabic',
        fontSize=12,
        leading=14,
        alignment=1,
    )

    # إنشاء محتوى التقرير
    elements = []
    
    # عنوان التقرير والتاريخ
    title = arabic_reshaper.reshape("تقرير المخزون")
    title = get_display(title)
    elements.append(Paragraph(title, title_style))
    
    current_date = datetime.now().strftime("%Y/%m/%d")
    date_str = arabic_reshaper.reshape(f"التاريخ: {current_date}")
    date_str = get_display(date_str)
    elements.append(Paragraph(date_str, normal_style))
    elements.append(Paragraph("<br/>", styles['Normal']))
    
    # جدول بكل الكتب
    table_data = [
        [
            get_display(arabic_reshaper.reshape("الكمية")),
            get_display(arabic_reshaper.reshape("الحجم")),
            get_display(arabic_reshaper.reshape("الرواية")),
            get_display(arabic_reshaper.reshape("التصنيف")),
            get_display(arabic_reshaper.reshape("اسم الكتاب"))
        ]
    ]
    
    for book in books:
        riwaya = book.riwaya if book.riwaya else "-"
        table_data.append([
            str(book.quantity),
            get_display(arabic_reshaper.reshape(book.size)),
            get_display(arabic_reshaper.reshape(riwaya)),
            get_display(arabic_reshaper.reshape(book.category)),
            get_display(arabic_reshaper.reshape(book.title))
        ])
    
    table = Table(table_data, colWidths=[40, 60, 100, 100, 200])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'NotoNaskhArabic'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)
    
    # إجمالي عدد الكتب في النهاية
    elements.append(Paragraph("<br/>", styles['Normal']))
    total = arabic_reshaper.reshape(f"إجمالي عدد الكتب: {total_books}")
    total = get_display(total)
    elements.append(Paragraph(total, normal_style))
    
    # إنشاء التقرير
    doc.build(elements)
    
    return send_file(pdf_file, as_attachment=True, download_name='تقرير_المخزون.pdf')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin)
            db.session.commit()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
