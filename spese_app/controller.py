from functools import wraps
from datetime import datetime, date
import os

from flask import *
from flask_login import LoginManager, login_user, current_user, logout_user

from spese_app.model import *
from spese_app.forms import *

app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']

# login manager initialization
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
	return session.query(User).get(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
	form = LoginForm(request.form)
	
	if form.validate_on_submit() and request.method=='POST':
		user_to_log = authenticate_user(
			apartment = form.apartment.data,
			username = form.username.data,
			password = form.password.data
		)

		if user_to_log:
			login_user(user_to_log, remember=False)
			# return redirect(url_for("main_page"))
		else:
			flash("Password o username errati")
	return render_template("login.html", form=form)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
	if current_user.is_authenticated:
		logout_user()
	return redirect(url_for("login"))
