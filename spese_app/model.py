import datetime
import os
from collections import OrderedDict

from sqlalchemy import create_engine, Table, Column, ForeignKey, Integer, String, DateTime, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

__all__ = ['Tenant', 'Expense', 'session', 'compute_tenants_credits', 'compute_total_expenses']

# read configuration from environment variable to connect db
engine = create_engine(os.environ['POSTGRE_DB'])

# create sqlalchemy needed objects
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

class Tenant(Base):
	"""
		Object describing a tenant of the apartment
	"""
	__tablename__ = 'tenants'
	id = Column(Integer, primary_key=True)
	name = Column(String, nullable=False)
	surname = Column(String, nullable=False)
	expenses_as_buyer = relationship("Expense", back_populates="payer", cascade="all")

	expenses_as_involved = relationship("Expense",
		secondary=involved_tenants_expense,
		back_populates="involved_tenants"
	)

	def __init__(self, name, surname):
		self.name = name
		self.surname = surname

	def desc(self):
		return {"id": self.id, "name": self.name, "surname": self.surname}

	def __repr__(self):
		# recursively retrieve descriptions of all attributes
		attributes = [item + "=" + repr(value) for item, value in self.desc().items()]
		return "<Tenant({})>".format(", ".join(attributes))

	def __str__(self):
		return "{} {}".format(self.name, self.surname)

	def __hash__(self):
		return self.id


class Expense(Base):
	"""
		Object describing an expense made by one tenant for some of the others
	"""
	__tablename__ = 'expenses'
	id = Column(Integer, primary_key=True)
	amount = Column(Float, nullable=False)

	payer_id = Column(Integer, ForeignKey('tenants.id'))
	payer = relationship("Tenant", back_populates="expenses_as_buyer")
	involved_tenants = relationship('Tenant', secondary=involved_tenants_expense, back_populates='expenses_as_involved')

	date_time = Column(DateTime, nullable=False)

	def __init__(self, payer, amount, date_time=None, involved_tenants=None):
		self.payer = payer
		self.amount = amount

		# set current if no date & time is given
		if date_time is None:
			self.date_time = datetime.datetime.now()
		else:
			self.date_time = date_time

		# if list of involved is not set, add all, else follow parameter
		if involved_tenants is None:
			for tenant in session.query(Tenant):
				self.involved_tenants.append(tenant)
		else:
			for involved_tenant in involved_tenants:
				self.involved_tenants.append(involved_tenant)

	def desc(self):
		return {"id": self.id, "payer": self.payer.desc(), "amount": self.amount, "date_time": self.date_time,
				"involved_tenants": [tenant.desc() for tenant in self.involved_tenants]}

	def __repr__(self):
		attributes = [item + "=" + repr(value) for item, value in self.desc().items()]
		return "<Expense({})>".format(", ".join(attributes))


# create all required tables according to classes before
Base.metadata.create_all(engine)

# compute financial situation according to expenses in database
def compute_tenants_credits():
	tenants = session.query(Tenant).order_by(Tenant.id)
	credits = OrderedDict(zip(tenants, [0] * tenants.count()))

	for expense in session.query(Expense):
		payer = expense.payer
		involved = expense.involved_tenants

		# set credit for payer
		credits[payer] += expense.amount

		# set debts for involved tenants
		for tenant in involved:
			credits[tenant] -= expense.amount/len(involved)
	return credits


def compute_total_expenses():
	total = 0
	for expense in session.query(Expense):
		total += expense.amount
	return total
