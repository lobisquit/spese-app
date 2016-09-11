from functools import wraps
from datetime import datetime, date

from flask import *
from flask_login import LoginManager, login_user, current_user, logout_user

from spese_app.model import *
from spese_app.forms import LoginForm

app = Flask(__name__)
app.secret_key = 'asdasd8atsd7r6872y12be019asdjho2182d9b'

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
		user = session.query(User).filter(
			User.username==form.username.data,
			User.password==form.password.data
		).first()
		if user!=None:
			login_user(user, remember=False)
			# return redirect(url_for("main_page"))
		else:
			flash("Password o username errati")
	return render_template("login.html", form=form)
