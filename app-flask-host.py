import sys
import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from functools import wraps
import json
from datetime import datetime


# Ensure the path to your app is in the system path
path = '/home/yourusername/mysite'
if path not in sys.path:
    sys.path.append(path)


# สร้างแอปพลิเคชัน Flask ขึ้นมา
app = Flask(__name__)
# กำหนดคีย์ลับ (SECRET_KEY) สำหรับแอปพลิเคชัน ซึ่งจะใช้ในการเข้ารหัสข้อมูลสำคัญ เช่น session cookies
app.config['SECRET_KEY'] = 'jirada_secret_key'
# กำหนด URI ของฐานข้อมูลที่แอปพลิเคชันจะเชื่อมต่อ โดยในที่นี้ใช้ฐานข้อมูล SQLite ที่ชื่อว่า blog.db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/adswebinfo/mysite/instance/blog.db' #'sqlite:///blog.db'
# ปิดการติดตามและแจ้งเตือนการเปลี่ยนแปลงของออบเจ็กต์ใน SQLAlchemy ซึ่งจะช่วยประหยัดทรัพยากรและปรับปรุงประสิทธิภาพของแอปพลิเคชัน
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# สร้างออบเจ็กต์ SQLAlchemy โดยส่งผ่านแอปพลิเคชัน Flask (app) เข้าไปใน SQLAlchemy ซึ่งจะช่วยในการจัดการและเชื่อมต่อกับฐานข้อมูล
db = SQLAlchemy(app)

# สร้างออบเจ็กต์ Bcrypt โดยส่งผ่านแอปพลิเคชัน Flask (app) เข้าไปใน Bcrypt ซึ่งจะใช้ในการเข้ารหัสรหัสผ่าน (password hashing)
bcrypt = Bcrypt(app)

# สร้างออบเจ็กต์ LoginManager โดยส่งผ่านแอปพลิเคชัน Flask (app) เข้าไปใน LoginManager
# ซึ่งจะช่วยจัดการการเข้าสู่ระบบ (login) และการควบคุมสิทธิ์การเข้าถึงของผู้ใช้
login_manager = LoginManager(app)

# กำหนดหน้าเว็บที่ผู้ใช้จะถูกนำไปเมื่อพยายามเข้าถึงหน้าที่ต้องการการเข้าสู่ระบบ
# แต่ยังไม่ได้เข้าสู่ระบบ โดยในที่นี้กำหนดให้ไปที่ login ซึ่งเป็นชื่อของ route
login_manager.login_view = 'login'


# User Model โมเดลนี้สร้างขึ้นเพื่อเก็บข้อมูลของผู้ใช้ในระบบ
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    level = db.Column(db.String(10), nullable=False, default='user')  # 'admin' or 'user'

# Post Model โมเดลนี้สร้างขึ้นเพื่อเก็บข้อมูลของโพสต์ในบล็อก
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Add this line

# ฟังก์ชันนี้จะถูกใช้โดย Flask-Login เพื่อโหลดข้อมูลผู้ใช้จากฐานข้อมูลโดยใช้ user_id ที่ถูกส่งมา
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper function to check admin status
# ฟังก์ชันนี้เป็นตัวช่วยในการตรวจสอบว่า
# ผู้ใช้ที่เข้าถึงเส้นทางนี้ต้องเป็นแอดมินเท่านั้น หากไม่ใช่แอดมินจะถูกบล็อกไม่ให้เข้าถึง โดยส่งโค้ด 403 (Forbidden)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.level != 'admin':
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

#----------------- Routes-Start FRONT-END ------------------------
# Routes
# Routes-ฟังก์ชันนี้จะดึงโพสต์ที่ยังใช้งานอยู่จากฐานข้อมูลมาแสดงบนหน้าแรก
@app.route('/')
def index():
    #posts = Post.query.order_by(Post.id.desc()).limit(6).all()
    posts = Post.query.filter_by(is_active=True).order_by(Post.id.desc()).limit(6).all()
    for post in posts:
        post.formatted_time = post.created_at.strftime('%d/%m/%y - %H:%M')  # Format time as dd/mm/yy - hh:mm
    return render_template('index.html', posts=posts)

# ฟังก์ชันนี้ใช้แสดงโพสต์แต่ละโพสต์ตาม id โดยจะลองแปลงเนื้อหาของโพสต์จาก JSON
@app.route('/blog/<int:id>', methods=['GET'])
def post(id):
    post = Post.query.get_or_404(id)
    try:
        # Parse JSON content
        content_data = json.loads(post.content)
        # Extract text from JSON and convert it to HTML
        html_content = ''.join(block['data']['text'] for block in content_data['blocks'])
    except (json.JSONDecodeError, KeyError):
        html_content = "Invalid content format / รูปแบบเนื้อหาไม่ถูกต้อง"
    return render_template('blog.html', post=post, content_html=html_content)

#----------------- Routes-End FRONT-END ------------------------


#----------------- Routes-Start BACK-END ------------------------
# ฟังก์ชันนี้ใช้ในการจัดการโพสต์ โดยแสดงโพสต์สูงสุด 100 โพสต์ เรียงตามลำดับเวลา
@app.route('/manage_post')
@login_required
@admin_required
def manage_post():
    #posts = Post.query.all()
    #return render_template('manage.html', posts=posts)
    posts = Post.query.order_by(Post.id.desc()).limit(100).all()
    for post in posts:
        post.formatted_time = post.created_at.strftime('%d/%m/%y - %H:%M')  # Format time as dd/mm/yy - hh:mm
    return render_template('manage_post.html', posts=posts)

# ฟังก์ชันนี้ใช้ในการเพิ่มโพสต์ใหม่ในระบบ โดยหลังจากเพิ่มโพสต์
@app.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        img_url = request.form['img_url']
        new_post = Post(title=title, content=content, img_url=img_url, created_at=datetime.utcnow())
        db.session.add(new_post)
        db.session.commit()
        flash('เพิ่มโพสต์เรียบร้อยแล้ว!', 'success')
        return redirect(url_for('index'))
    return render_template('add_post.html')

# ฟังก์ชันนี้ใช้สำหรับแก้ไขโพสต์ที่มีอยู่ โดยจะโหลดข้อมูลโพสต์เดิมมาจากฐานข้อมูลเพื่อแก้ไข
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_post(id):
    post = Post.query.get_or_404(id)
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        post.img_url = request.form['img_url']
        post.is_active = 'is_active' in request.form
        db.session.commit()
        flash('อัพเดทโพสต์เรียบร้อยแล้ว!', 'success')
        return redirect(url_for('index'))
    return render_template('edit_post.html', post=post)

# ฟังก์ชันนี้ใช้สำหรับสลับสถานะของโพสต์ว่าโพสต์นี้จะถูกแสดงหรือไม่ (เปิด/ปิดการแสดงผล)
@app.route('/toggle/<int:id>', methods=['GET'])
@login_required
@admin_required
def toggle_post(id):
    post = Post.query.get_or_404(id)
    post.is_active = not post.is_active
    db.session.commit()
    return redirect(url_for('manage_post'))

# User Authentication Routes
# ฟังก์ชันนี้ใช้สำหรับเข้าสู่ระบบ โดยตรวจสอบชื่อผู้ใช้และรหัสผ่านว่าถูกต้องหรือไม่
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('manage_post',user=user))
        else:
            flash('การเข้าสู่ระบบล้มเหลว ตรวจสอบชื่อผู้ใช้และรหัสผ่านของคุณ', 'danger')
    return render_template('login.html')

# ฟังก์ชันนี้ใช้สำหรับออกจากระบบ โดยเมื่อออกจากระบบสำเร็จแล้วจะกลับไปที่หน้าแรก
@app.route('/logout')
@login_required
def logout():
    logout_user()  # This logs out the current user
    flash('คุณออกจากระบบสำเร็จแล้ว', 'success')
    return redirect(url_for('index'))  # Redirect to the homepage after logout

# ฟังก์ชันนี้ใช้สำหรับสมัครสมาชิกใหม่ โดยบันทึกข้อมูลผู้ใช้ลงฐานข้อมูล
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('สร้างบัญชีสำเร็จแล้ว! คุณสามารถเข้าสู่ระบบได้แล้ว', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# ฟังก์ชันนี้ใช้ในการจัดการผู้ใช้ โดยแสดงรายชื่อผู้ใช้ทั้งหมดที่มีอยู่ในระบบ
@app.route('/manage_user')
@login_required
@admin_required
def manage_user():
    users = User.query.all()  # Fetch all users from the database
    return render_template('manage_user.html', users=users)

# ฟังก์ชันนี้ใช้สำหรับแก้ไขข้อมูลผู้ใช้ โดยสามารถแก้ไขชื่อผู้ใช้และระดับการเข้าถึง (user/admin)
@app.route('/edit_user/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.username = request.form['username']
        user.level = request.form['level']
        db.session.commit()
        flash('อัปเดตผู้ใช้สำเร็จแล้ว!', 'success')
        return redirect(url_for('manage_user'))  # Correct endpoint used here
    return render_template('edit_user.html', user=user)

# ฟังก์ชันนี้ใช้ในการอัปเดตข้อมูลผู้ใช้ที่มีอยู่ โดยจะบันทึกการเปลี่ยนแปลงลงในฐานข้อมูล
@app.route('/update_user/<int:id>', methods=['POST'])
@login_required
@admin_required
def update_user(id):
    user = User.query.get_or_404(id)
    user.username = request.form['username']
    user.level = request.form['level']
    db.session.commit()
    flash('อัปเดตผู้ใช้สำเร็จแล้ว!', 'success')
    return redirect(url_for('manage_user'))

# ฟังก์ชันนี้ใช้ในการแสดงข้อมูลโปรไฟล์ของผู้ใช้ที่เข้าสู่ระบบอยู่ในปัจจุบัน
@app.route('/profile', methods=['GET'])
@login_required
def profile():
    return render_template('profile.html')

# ฟังก์ชันนี้ใช้สำหรับเปลี่ยนรหัสผ่าน
@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    old_password = request.form['old_password']
    new_password = request.form['new_password']

    if bcrypt.check_password_hash(current_user.password, old_password):
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        current_user.password = hashed_password
        db.session.commit()
        flash('รหัสผ่านของคุณได้รับการอัพเดตแล้ว!', 'success')
    else:
        flash('รหัสผ่านเก่าไม่ถูกต้อง', 'danger')
    return redirect(url_for('profile'))

#----------------- Routes-END BACK-END ------------------------

# Custom 404 Error Handler
# กำหนดให้ฟังก์ชันนี้ทำงานเมื่อเกิดข้อผิดพลาดประเภท 404 (Not Found)
@app.errorhandler(404)

# ฟังก์ชัน not_found_error ทำหน้าที่จัดการกับข้อผิดพลาด 404 โดย:
# แสดงหน้าเว็บ index.html พร้อมส่งข้อความ
# ส่งรหัสสถานะ HTTP 404 กลับไปยังเบราว์เซอร์ เพื่อบอกว่าหน้านี้ไม่พบจริงๆ
def not_found_error(error):
    return render_template('index.html', error_message='ไม่พบหน้าที่คุณกำลังค้นหา กรุณาตรวจสอบ URL และลองใหม่อีกครั้ง'), 404

#if __name__ == '__main__':
#    with app.app_context():
#        db.create_all()
#    app.run(debug=True)
# Set the environment variable for Flask if needed
db.create_all()
os.environ['FLASK_ENV'] = 'production'
from flask_app import app as application
