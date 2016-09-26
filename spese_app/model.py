import datetime
import os
from collections import OrderedDict

from sqlalchemy_utils.types.password import PasswordType
from bcrypt import gensalt, hashpw

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from flask_login import UserMixin

__all__ = ['Apartment', 'User', 'Tenant', 'Expense', 'session',
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

class Apartment(MyMixin, Base):
	"""
		Describe apartment with admin, trusted_user and tenants
	"""
	__tablename__ = 'apartments'
	id = Column(Integer, primary_key=True)
	name = Column(String, unique=True)
	users = relationship('User')

	def desc(self):
		return {'name': self.name}

class User(MyMixin, Base, UserMixin):
	"""
		Object describing a user of the system, even non tenant ones
	"""
	__tablename__ = 'users'
	id = Column(Integer, primary_key=True)
	apartment = relationship('Apartment')
	apartment_id = Column(Integer, ForeignKey('apartments.id'))

	username = Column(String, nullable=False)
	real_name = Column(String, nullable=True)
	password = Column(PasswordType(schemes=['bcrypt']))
	UniqueConstraint('username', 'apartment_id')

	type = Column(String)
	__mapper_args__ = {
		'polymorphic_on': type,
		'polymorphic_identity':'user'
	}

	def __init__(self, apartment=None, **kwargs):
		# fetch proper object if just name is given
		if isinstance(apartment, str):
			apartment = session.query(Apartment).filter(
				Apartment.name==apartment
			).one()
		super().__init__(apartment=apartment, **kwargs)

	def desc(self):
		return {
			'id': self.id,
			'username': self.username,
			'real_name': self.real_name,
			'password': '***', # displaying a Password object is not useful
			'apartment': self.apartment
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
	expenses_as_buyer = relationship('Expense', back_populates='payer', cascade='all')
	expenses_as_involved = relationship(
		'Expense',
		secondary=involved_tenants_expense,
		back_populates='involved_tenants'
	)

	__mapper_args__ = {
		'polymorphic_identity':'tenant'
	}

	def desc(self):
		return dict(super().desc(), **{'real_name': self.real_name})

	def __str__(self):
		if real_name is None:
			return self.username
		else:
			return self.real_name


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

	def __init__(self, date_time=None, involved_tenants=None, **kwargs):
		"""
			If None, date_time is set to now
			If None, involved_tenants is set to all tenants of payer's apartment
		"""
		# set current if no date & time is given
		if date_time is None:
			date_time = datetime.datetime.now()

		# if list of involved is not set, add all, else follow parameter
		if involved_tenants is None:
			involved_tenants = []
			for tenant in session.query(Tenant).filter(Tenant.apartment==kwargs['payer'].apartment):
				involved_tenants.append(tenant)

		super().__init__(date_time=date_time, involved_tenants=involved_tenants, **kwargs)

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


def compute_tenants_credits(apartment):
	"""
		Compute financial situation of given apartment according to expenses in database
	"""
	# get all Tenants of given apartment
	tenants = session.query(Tenant).join(Apartment).filter(Apartment.name==apartment).order_by(Tenant.id)
	credits = OrderedDict(zip(tenants, [0] * tenants.count()))

	# get all Expenses referring to tenants of given apartment
	for expense in session.query(Expense).join(Tenant).join(Apartment).filter(Apartment.name==apartment):
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
	for expense in session.query(Expense).join(Tenant).join(Apartment).filter(Apartment.name==apartment):
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
