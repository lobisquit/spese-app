import unittest
import os
from spese_app.model import *

class TestStringMethods(unittest.TestCase):
	def test_add_tenant(self):
		new_tenant = Tenant("John", "Doe")
		session.add(new_tenant)
		session.commit()
		assert session.query(Tenant).get(new_tenant.id) is not None
		session.delete(new_tenant)

	def test_expense_when_its_payer_is_deleted(self):
		tenant = Tenant("John", "Doe")
		expense = Expense(tenant, 10)
		session.add(tenant)
		session.add(expense)
		session.commit()

		expense_id = expense.id
		session.delete(tenant)
		session.commit()
		# # activate for further inspection
		# print(session.query(Expense).get(expense_id))
		assert session.query(Expense).get(expense_id) is None

if __name__ == '__main__':
	unittest.main()
