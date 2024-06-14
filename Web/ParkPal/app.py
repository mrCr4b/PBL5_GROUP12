from flask import Flask, render_template, request, session, redirect, url_for, flash, send_file
from flask_mysqldb import MySQL
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from flask_bcrypt import Bcrypt
from AccountDetailForm import AccountDetailForm
from io import BytesIO
import requests
import io

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'parkpal'

mysql = MySQL(app)
bcrypt = Bcrypt(app)

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Sign Up')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        
        if request.method == 'POST':
            # Check if the email already exists
            cur = mysql.connection.cursor()
            result = cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            if result > 0:
                flash('Email already exists. Please use a different email.', 'danger')
                cur.close()
                return redirect(url_for('register'))

            # Hash the password
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            # Insert the new user into the database
            cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, hashed_password))
            mysql.connection.commit()
            cur.close()

            flash('Account created successfully!', 'success')
            return redirect(url_for('login'))
        
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Retrieve user data from the database
        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        if result > 0:
            user = cur.fetchone()
            # Lấy danh sách các tên cột từ kết quả trả về
            column_names = [description[0] for description in cur.description]
            # Lấy index của cột 'password'
            password_index = column_names.index('password')
            # Lấy index của cột 'role'
            role_index = column_names.index('role')
            if bcrypt.check_password_hash(user[password_index], password):
                if user[role_index] == 'user':
                    # Lưu thông tin người dùng vào session
                    session['user'] = user
                    flash('Logged in successfully!', 'success')

                    # Kiểm tra xem thông tin chi tiết tài khoản có sẵn không
                    result_detail = cur.execute("SELECT * FROM account_detail WHERE user_id = %s", (user[0],))
                    if result_detail > 0:
                        user_detail = cur.fetchone()
                        session['user_detail'] = user_detail

                    return redirect(url_for('index'))
                elif user[role_index] == 'admin':
                    # Lưu thông tin người dùng vào session
                    session['user'] = user
                    flash('Logged in successfully as admin!', 'success')
                    return redirect(url_for('admin'))
            else:
                flash('Incorrect password. Please try again.', 'danger')
        else:
            flash('Email not found. Please register.', 'danger')
        cur.close()
    return render_template('login.html', form=form)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    try:
        if request.method == 'POST':
            search_query = request.form.get('search')
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM parking WHERE car_number LIKE %s", ('%' + search_query + '%',))
            parking_data = cur.fetchall()
            cur.close()
        else:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM parking")
            parking_data = cur.fetchall()
            cur.close()
            
        # Tìm số lượng xe trong hệ thống, đang đỗ và số lượng chỗ còn trống
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM car_plates")
        so_luong_xe = cur.fetchone()[0]
        cur.close()
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM parking WHERE time_out IS NULL")
        result = cur.fetchone()
        dang_do = result[0] if result else 0
        cur.close()
                
        cho_trong = 200 - dang_do
        # Phân loại xe đang đỗ và xe đã đỗ
        currently_parked = [row for row in parking_data if row[4] is None]
        exited_parked = [row for row in parking_data if row[4] is not None]

        return render_template('admin.html', currently_parked=currently_parked, exited_parked=exited_parked, so_luong_xe=so_luong_xe, dang_do=dang_do, cho_trong=cho_trong)
    except Exception as e:
        print("Error fetching parking data:", e)
        return "An error occurred while fetching parking data"
    
@app.route('/image/<int:parking_id>/<string:image_type>')
def image(parking_id, image_type):
    try:
        cur = mysql.connection.cursor()
        
        if image_type == 'in':
            cur.execute("SELECT image_in FROM parking WHERE id=%s", (parking_id,))
        elif image_type == 'out':
            cur.execute("SELECT image_out FROM parking WHERE id=%s", (parking_id,))
        
        image_blob = cur.fetchone()[0]
        cur.close()

        if image_blob:  # Kiểm tra dữ liệu hình ảnh không rỗng
            return send_file(io.BytesIO(image_blob), mimetype='image/jpeg')
        else:
            return "Image not found"
    except Exception as e:
        print("Error fetching image:", e)
        return "An error occurred while fetching the image"
    
@app.route('/update_account_detail', methods=['POST'])
def update_account_detail():
    if 'user' in session:
        user_id = session['user'][0]
        name = request.form.get('name')
        birthday = request.form.get('birthday')
        cccd = request.form.get('cccd')
        start_day = request.form.get('start_day')
        end_day = request.form.get('end_day')
        car_plates = request.form.getlist('car_plates')

        try:
            cur = mysql.connection.cursor()
            fields_to_update = []
            values_to_update = []

            # Kiểm tra các trường không rỗng và thêm vào danh sách các trường cần cập nhật
            if name:
                fields_to_update.append("Name = %s")
                values_to_update.append(name)
            if birthday:
                fields_to_update.append("birthday = %s")
                values_to_update.append(birthday)
            if cccd:
                fields_to_update.append("cccd = %s")
                values_to_update.append(cccd)
            if start_day:
                fields_to_update.append("start_day = %s")
                values_to_update.append(start_day)
            if end_day:
                fields_to_update.append("end_day = %s")
                values_to_update.append(end_day)

            # Chỉ cập nhật nếu có ít nhất một trường không rỗng
            if fields_to_update:
                sql_query = "UPDATE account_detail SET " + ", ".join(fields_to_update) + " WHERE user_id = %s"
                values_to_update.append(user_id)  # Thêm user_id vào cuối danh sách giá trị
                cur.execute(sql_query, values_to_update)

            # Xóa các biển số xe cũ của user này
            cur.execute("DELETE FROM car_plates WHERE user_id = %s", (user_id,))

            # Thêm các biển số xe mới
            for plate in car_plates:
                if plate:  # Chỉ thêm biển số xe nếu không rỗng
                    cur.execute("INSERT INTO car_plates (user_id, plate_number) VALUES (%s, %s)", (user_id, plate))

            # Lưu các thay đổi vào database
            mysql.connection.commit()
            cur.close()
            flash('Account details updated successfully!', 'success')
            return redirect(url_for('account_details', user_id=user_id))
        except Exception as e:
            flash(f'An error occurred while updating account details: {e}', 'danger')
            return redirect(url_for('account_details', user_id=user_id))
    else:
        flash('Please log in to update your account details.', 'danger')
        return redirect(url_for('login'))



@app.route('/')
def index():
    # Lấy thông tin người dùng từ session
    user = session.get('user')
    if user:
        # Truy vấn danh sách biển số xe từ cơ sở dữ liệu
        cur = mysql.connection.cursor()
        cur.execute("SELECT plate_number FROM car_plates WHERE user_id = %s", (user[0],))
        car_plates = cur.fetchall()
        cur.close()

        # Trả về trang chính với thông tin người dùng và danh sách biển số xe
        return render_template('index.html', user=user, car_plates=car_plates)
    else:
        # Nếu không có thông tin người dùng trong session, chuyển hướng đến trang đăng nhập
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    # Xóa thông tin người dùng khỏi session
    session.pop('user', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/gioi-thieu')
def gioi_thieu():
    return render_template('gioi-thieu.html')

@app.route('/nhan-dan-tieng-viet')
def nhan_dan_tieng_viet():
    return render_template('nhan-dan-tieng-viet.html')

@app.route('/lien-he')
def lien_he():
    return render_template('lien-he.html')

def save_search_history(user_id, query):
    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO search_history (user_id, query) VALUES (%s, %s)", (user_id, query))
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        mysql.connection.rollback()
        print("Error saving search history:", e)

@app.route('/update_car_plates', methods=['POST'])
def update_car_plates():
    if 'user' in session:
        user_id = session['user'][0]
        car_plates = request.form.getlist('car_plates[]')

        cur = mysql.connection.cursor()
        try:
            # Xóa các biển số xe hiện tại
            cur.execute("DELETE FROM car_plates WHERE user_id = %s", (user_id,))
            
            # Thêm các biển số xe mới
            for plate in car_plates:
                cur.execute("INSERT INTO car_plates (user_id, plate_number) VALUES (%s, %s)", (user_id, plate))
            
            # Lưu các thay đổi vào cơ sở dữ liệu
            mysql.connection.commit()
        except Exception as e:
            mysql.connection.rollback()
            print("Lỗi khi cập nhật biển số xe:", e)
            return "Đã có lỗi xảy ra khi cập nhật biển số xe.", 500
        finally:
            cur.close()
        
        return redirect('/')
    else:
        return redirect('/login')


@app.route('/account_details/<int:user_id>', methods=['GET'])
def account_details(user_id):
    try:
        # Lấy thông tin chi tiết tài khoản từ bảng account_detail
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM account_detail WHERE user_id = %s", (user_id,))
        account_detail = cur.fetchone()

        # Lấy danh sách biển số xe từ bảng car_plates
        cur.execute("SELECT plate_number FROM car_plates WHERE user_id = %s", (user_id,))
        car_plates = cur.fetchall()

        # Đóng kết nối
        cur.close()

        if account_detail:
            # Chuẩn bị dữ liệu để gửi đến template
            return render_template('account_details.html', 
                                   account_detail=account_detail, 
                                   car_plates=car_plates)
        else:
            flash('Account details not found.', 'danger')
            return redirect(url_for('index'))
    except Exception as e:
        flash('An error occurred while retrieving account details.', 'danger')
        return redirect(url_for('index'))
    
@app.route('/history')
def history():
    # Kiểm tra nếu user đã đăng nhập
    if 'user' in session:
        user_id = session['user'][0]
        
        # Truy vấn dữ liệu lịch sử ra vào từ database cho user hiện tại
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM parking WHERE id_user = %s", (user_id,))
        parking_data = cur.fetchall()
        cur.close()
        
        # Phân loại xe đang đỗ và xe đã rời bãi
        currently_parked = [row for row in parking_data if row[4] is None]
        exited_parked = [row for row in parking_data if row[4] is not None]

        return render_template('history.html', currently_parked=currently_parked, exited_parked=exited_parked)
    else:
        flash('Please log in to view your parking history.', 'danger')
        return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
