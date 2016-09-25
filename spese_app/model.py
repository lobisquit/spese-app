import datetime
import os
from collections import OrderedDict

from sqlalchemy_utils.types.password import PasswordType
from bcrypt import gensalt, hashpw

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from flask_login import UserMixin

__all__ = ['Role', 'User', 'Tenant', 'Expense', 'session',
	'compute_tenants_credits', 'compute_total_expenses', 'authenticate_user']

# read configuration from environment variable to connect db
engine = create_engine(os.environ['POSTGRE_DB'])

# create sqlalchemy basic objects
Base = declarative_base()

Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

# create many-to-many association table between tenants and expenses
involved_tenants_expense = Table(
	'buyer_expense',
	Base.metadata,
	Column('expense_id', ForeignKey('expenses.id'), primary_key=True),
	Column('tenant_id', ForeignKey('tenants.id'), primary_key=True)
)

class MyMixin():
	def desc():
		""" Return a dictionary with all <attr:value> entries """
		return NotImplemented

	def __repr__(self):
		"""
			Redefine repr built-in function to print object description in format:
				<Object(attr1=value1, attr2=value2, ...)>
			All attributes are read from self.desc() custom function.
		"""
		attributes = [item + '=' + repr(value) for item, value in self.desc().items()]
		return '<{0}({1})>'.format(
			self.__class__.__name__,
			', '.join(attributes)
		)


class Role(Base, MyMixin):
	"""
		Define basic role of access
	"""
	__tablename__ = 'roles'
	id = Column(Integer, primary_key=True)
	name = Column(String, unique=True)
	users = relationship('User', back_populates='role')

	def __init__(self, name):
		self.name = name

	def desc(self):
		return {'name': self.name}

	def __str__(self):
		return self.name

	def __hash__(self):
		return hash(self.name)


class User(MyMixin, Base, UserMixin):
	"""
		Object describing a user of the system, even non tenant ones
	"""
	__tablename__ = 'users'
	id = Column(Integer, primary_key=True)
	apartment = Column(String)
	username = Column(String, nullable=False)
	password = Column(PasswordType(schemes=['bcrypt']))

	role_id = Column(Integer, ForeignKey('roles.id'))
	role = relationship('Role')

	type = Column(String)
	__mapper_args__ = {
		'polymorphic_on': type,
		'polymorphic_identity':'user'
	}

	def __init__(self, role=None, password=None, **kwargs):
		"""
			Available arguments are these:
				- role, a model.Role object
				- apartment, as a string
				- username
				# - password
		"""
		if role is None:
			# if no role is set, guess it via username (else fail)
			role = session.query(Role).filter(Role.name==kwargs['username']).one()
		self.password = password
		super().__init__(role=role, **kwargs)

	def desc(self):
		return {
			'id': self.id,
			'username': self.username,
			# displaying a Password object is meaningless
			'password': '***',
			'apartment': self.apartment,
			'role': self.role
		}

	def is_tenant(self):
		"""
			Tell if given User object is Tenant (i.e. can have expenses associated)
		"""
		return isinstance(self, Tenant)


class Tenant(User):
	"""
		Object describing a tenant of the apartment
	"""
	__tablename__ = 'tenants'
	id = Column(Integer, ForeignKey('users.id'), primary_key=True)
	real_name = Column(String, nullable=False)

	expenses_as_buyer = relationship('Expense', back_populates='payer', cascade='all')
	expenses_as_involved = relationship(
		'Expense',
		secondary=involved_tenants_expense,
		back_populates='involved_tenants'
	)

	__mapper_args__ = {
		'polymorphic_identity':'tenant'
	}

	def __init__(self, real_name=None, **kwargs):
		"""
			Available arguments are these:
				- role, a model.Role object
				- apartment, as a string
				- username
				- password
				- real user name
		"""
		tenant_role = session.query(Role).filter(Role.name=='tenant').one()
		super().__init__(role=tenant_role, **kwargs)
		self.real_name = real_name

	def desc(self):
		return dict(super().desc(), **{'real_name': self.real_name})

	def __str__(self):
		return '{} {}'.format(self.name, self.surname)


class Expense(MyMixin, Base):
	"""
		Object describing an expense made by one tenant for some of the others
	"""
	__tablename__ = 'expenses'
	id = Column(Integer, primary_key=True)
	amount = Column(Float, nullable=False)
	date_time = Column(DateTime, nullable=False)

	payer_id = Column(Integer, ForeignKey('tenants.id'))
	payer = relationship('Tenant')
	involved_tenants = relationship('Tenant', secondary=involved_tenants_expense)

	def __init__(self, payer, amount, date_time=None, involved_tenants=None):
		"""
			If None, date_time is set to now
			If None, involved_tenants is set to all tenants of payer's apartment
		"""
		self.payer = payer
		self.amount = amount

		# set current if no date & time is given
		if date_time is None:
			self.date_time = datetime.datetime.now()
		else:
			self.date_time = date_time

		# if list of involved is not set, add all, else follow parameter
		if involved_tenants is None:
			for tenant in session.query(Tenant).filter(Tenant.apartment==payer.apartment):
				self.involved_tenants.append(tenant)
		else:
			for involved_tenant in involved_tenants:
				self.involved_tenants.append(involved_tenant)

	def desc(self):
		return {
			'id': self.id,
			'payer': self.payer,
			'amount': self.amount,
			'date_time': self.date_time,
			'involved_tenants': self.involved_tenants
		}


# create all required tables according to classes before
Base.metadata.create_all(engine)

# populate roles in there is none
if session.query(Role).count() == 0:
	default_roles = [
		Role('root'),
		Role('admin'),
		Role('trusted_user'),
		Role('tenant')
	]
	session.add_all(default_roles)
	session.commit()

def compute_tenants_credits(apartment):
	"""
		Compute financial situation of given apartment according to expenses in database
	"""
	# get all Tenants of given apartment
	tenants = session.query(Tenant).filter(Tenant.apartment==apartment).order_by(Tenant.id)
	credits = OrderedDict(zip(tenants, [0] * tenants.count()))

	# get all Expenses referring to tenants of given apartment
	for expense in session.query(Expense).join(Tenant).filter(Tenant.apartment==apartment):
		payer = expense.payer
		involved = expense.involved_tenants

		# set credit for payer
		credits[payer] += expense.amount

		# set debts for involved tenants
		for tenant in involved:
			credits[tenant] -= expense.amount/len(involved)
	return credits


def compute_total_expenses(apartment):
	""" Get sum of all expenses for given apartment """
	total = 0
	# get all Expenses referring to tenants of given apartment
	for expense in session.query(Expense).join(Tenant).filter(Tenant.apartment==apartment):
		total += expense.amount
	return total

def authenticate_user(apartment=None, username=None, password=None):
	# special handle for root, that has no apartment
	if username=='root' and apartment=="":
		# note that "root" is unique and always present
		root = session.query(User).filter(User.username == 'root').one()
		if root.password == password:
			return root
	else:
		# handle common users (related to an apartment)
		# note that (username, apartment) is unique in database
		user = session.query(User).filter(
			User.username == username,
			User.apartment == apartment
		).one_or_none()
		# verify that such user exists too, i.e. it is not None
		if user and user.password == form.password.data:
			return user
	return None
