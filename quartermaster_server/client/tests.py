from django.test import TestCase

from client import quartermaster_client as qc

class TestViews(TestCase):
    def test_pass(self):
        print(dir(qc))
