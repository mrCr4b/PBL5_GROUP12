from wtforms import StringField, DateField, SubmitField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm

class AccountDetailForm(FlaskForm):
    card_number = StringField('Số thẻ', validators=[DataRequired()])
    name = StringField('Tên', validators=[DataRequired()])
    birthday = DateField('Ngày sinh', format='%Y-%m-%d', validators=[DataRequired()])
    cccd = StringField('CCCD', validators=[DataRequired()])
    start_day = DateField('Ngày bắt đầu', format='%Y-%m-%d', validators=[DataRequired()])
    end_day = DateField('Ngày kết thúc', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Cập nhật')
