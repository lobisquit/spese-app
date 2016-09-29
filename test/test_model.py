import unittest
import os
from spese_app.model import *
from spese_app.model import engine, Session

class TestStringMethods(unittest.TestCase):
	def setUp(self):
		session = Session()
		session.begin_nested()

	def tearDown(self):
		session.rollback()
		engine.dispose()

	def test_is_tenant(self):
		session.add(Apartment(name='Dorighello'))

		user = User(
			apartment='Dorighello',
			username='admin',
			password='password'
		)
		tenant = Tenant(
			apartment='Dorighello',
			username='enrico',
			password='password',
			real_name='Enrico'
		)
		self.assertTrue(tenant.is_tenant())
		self.assertFalse(user.is_tenant())

	def test_user_not_in_db_before_session_add(self):
		session.add(Apartment(name='Dorighello'))

		prev_number = session.query(User).count()
		tenant = Tenant(
			apartment='Dorighello',
			username='enrico',
			password='password',
			real_name='Enrico'
		)
		after_number = session.query(User).count()
		self.assertEqual(prev_number, after_number)

	def test_expense_not_in_db_before_session_add(self):
		session.add(Apartment(name='Dorighello'))

		prev_number = session.query(User).count()
		tenant = Tenant(
			apartment='Dorighello',
			username='enrico',
			password='password',
			real_name='Enrico'
		)
		after_number = session.query(User).count()
		self.assertEqual(prev_number, after_number)

	def test_add_tenant(self):
		session.add(Apartment(name='Dorighello'))

		tenant = Tenant(
			apartment='Dorighello',
			username='enrico',
			password='password',
			real_name='Enrico'
		)
		session.add(tenant)
		session.flush()
		assert session.query(Tenant).get(tenant.id) is not None
		session.delete(tenant)

	def test_add_expense(self):
		session.add(Apartment(name='Dorighello'))

		tenant = Tenant(
			apartment='Dorighello',
			username='enrico',
			password='password',
			real_name='Enrico'
		)
		expense = Expense(payer=tenant, amount=10)
		session.add(expense)
		session.flush()
		assert session.query(Expense).get(expense.id) is not None
		session.delete(expense)
		session.delete(tenant)

	def test_expense_disappear_when_its_payer_is_deleted(self):
		session.add(Apartment(name='Dorighello'))

		# behaviour obtained adding 'cascade="all"' to expenses_as_buyer in Tenant
		tenant = Tenant(
			apartment='Dorighello',
			username='enrico',
			password='password',
			real_name='Enrico'
		)
		expense = Expense(payer=tenant, amount=10)
		session.add(tenant)
		session.add(expense)
		session.flush()

		expense_id = expense.id
		session.delete(tenant)
		session.flush()
		# # activate for further inspection
		# print(session.query(Expense).get(expense_id))
		assert session.query(Expense).get(expense_id) is None

	def test_append_involved_tenants(self):
		session.add(Apartment(name='Dorighello'))
		session.add(Apartment(name='Portello'))

		tenant1 = Tenant(
			apartment='Dorighello',
			username='enrico',
			password='password',
			real_name='Enrico'
		)
		tenant2 = Tenant(
			apartment='Portello',
			username='jeje',
			password='password',
			real_name='Je'
		)
		session.add(tenant1)
		session.add(tenant2)

		expense = Expense(
			payer=tenant1,
			amount=10,
			involved_tenants=[tenant1]
		)
		session.add(expense)
		session.flush()
		self.assertEqual(expense.involved_tenants[0], tenant1)

		expense.involved_tenants.append(tenant2)
		self.assertEqual(expense.involved_tenants, [tenant1, tenant2])
		session.delete(tenant1)
		session.delete(tenant2)

	def test_compute_credits_all_involved(self):
		session.add(Apartment(name='Dorighello'))

		tenant1 = Tenant(apartment='Dorighello', username='enrico',
			password='password', real_name='')
		tenant2 = Tenant(apartment='Dorighello', username='pippo',
			password='password', real_name='')
		tenant3 = Tenant(apartment='Dorighello', username='pluto',
			password='password', real_name='')

		session.add(tenant1)
		session.add(tenant2)
		session.add(tenant3)

		expense = Expense(payer=tenant1, amount=9)
		session.add(expense)
		session.flush()

		self.assertEqual(
			compute_tenants_credits('Dorighello'),
			{tenant1: 6, tenant2: -3, tenant3: -3}
		)

	def test_compute_credits_not_payer_not_involved(self):
		session.add(Apartment(name='Dorighello'))

		tenant1 = Tenant(apartment='Dorighello', username='enrico',
			password='password', real_name='')
		tenant2 = Tenant(apartment='Dorighello', username='pippo',
			password='password', real_name='')
		tenant3 = Tenant(apartment='Dorighello', username='pluto',
			password='password', real_name='')

		session.add(tenant1)
		session.add(tenant2)
		session.add(tenant3)

		expense = Expense(payer=tenant1, amount=10, involved_tenants=[tenant1, tenant2])
		session.add(expense)
		session.flush()

		self.assertEqual(
			compute_tenants_credits('Dorighello'),
			{tenant1: 5, tenant2: -5, tenant3: -0}
		)

	def test_compute_credits_payer_non_involved(self):
		session.add(Apartment(name='Dorighello'))

		tenant1 = Tenant(apartment='Dorighello', username='enrico',
			password='password', real_name='')
		tenant2 = Tenant(apartment='Dorighello', username='pippo',
			password='password', real_name='')
		tenant3 = Tenant(apartment='Dorighello', username='pluto',
			password='password', real_name='')

		session.add(tenant1)
		session.add(tenant2)
		session.add(tenant3)

		expense = Expense(payer=tenant1, amount=9, involved_tenants=[tenant2, tenant3])
		session.add(expense)
		session.flush()

		self.assertEqual(
			compute_tenants_credits('Dorighello'),
			{tenant1: 9, tenant2: -4.5, tenant3: -4.5}
		)

	def test_compute_credits_with_other_apartments_tenants(self):
		session.add(Apartment(name='Dorighello'))
		session.add(Apartment(name='Portello'))

		tenant1 = Tenant(apartment='Dorighello', username='enrico',
			password='password', real_name='')
		tenant2 = Tenant(apartment='Dorighello', username='pippo',
			password='password', real_name='')
		tenant3 = Tenant(apartment='Dorighello', username='pluto',
			password='password', real_name='')
		alien_tenant = Tenant(apartment='Portello', username='paperino',
			password='password', real_name='')

		session.add(tenant1)
		session.add(tenant2)
		session.add(tenant3)
		session.add(alien_tenant)

		session.add(Expense(payer=tenant1, amount=9))
		session.add(Expense(payer=alien_tenant, amount=10))
		session.flush()

		self.assertEqual(
			compute_tenants_credits('Dorighello'),
			{tenant1: 6, tenant2: -3, tenant3: -3}
		)

	def test_password_encryption(self):
		session.query(User).all()
		user = User(username='test', password='password')
		session.add(user)
		session.commit()

		from sqlalchemy_utils.types.password import Password
		self.assertTrue(isinstance(user.password, Password))
		self.assertEqual(user.password, 'password')

		# delete user
		session.delete(user)

	def test_user_authentication(self):
		session.add(Apartment(name='posto'))
		session.add(User(apartment='posto', username='admin', password='password'))

		self.assertTrue(authenticate_user(apartment='posto', username='admin', password='password'))
		self.assertFalse(authenticate_user(apartment='other', username='admin', password='password'))
		self.assertFalse(authenticate_user(apartment='posto', username='wrong', password='password'))
		self.assertFalse(authenticate_user(apartment='posto', username='admin', password='wrong_password'))

		session.add(User(username='root', password='password'))
		self.assertTrue(authenticate_user(username='root', password='password'))

	def test_expense_and_tenants_deleted_when_apartment_deleted(self):
		apart = Apartment(name='Dorighello')
		session.add(apart)

		# behaviour obtained adding 'cascade="all"' to expenses_as_buyer in Tenant
		tenant = Tenant(
			apartment='Dorighello',
			username='enrico',
			password='password',
			real_name='Enrico'
		)
		expense = Expense(payer=tenant, amount=10)
		session.add(tenant)
		session.add(expense)
		session.flush()

		# save ids for testing
		expense_id = expense.id
		tenant_id = tenant.id

		# delete apartment and check cascade delete
		session.delete(apart)
		session.flush()

		assert session.query(Expense).get(expense_id) is None
		assert session.query(Tenant).get(tenant_id) is None
