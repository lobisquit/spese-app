from wtforms import StringField, PasswordField, SubmitField
from flask_wtf import Form
from wtforms.validators import DataRequired, NumberRange, Length, InputRequired

class LoginForm(Form):
	username = StringField(render_kw={'placeholder': 'Username'})
	password = PasswordField(render_kw={'placeholder': 'Password'})
	login_button = SubmitField('Login')
