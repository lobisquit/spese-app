from wtforms import StringField, PasswordField, SubmitField
from flask_wtf import Form
from wtforms.validators import DataRequired, NumberRange, Length, InputRequired

__all__ = ['LoginForm']


class LoginForm(Form):
	apartment = StringField('Appartamento')
	username = StringField('Nome utente')
	password = PasswordField('Password')
	login_button = SubmitField('Login')
