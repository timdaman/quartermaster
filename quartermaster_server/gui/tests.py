from django.contrib.auth.models import User
from django.test import TestCase
# Create your tests here.
from django.urls import reverse

from data.models import Pool, Resource


class GUITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="TEST_USER",
                                                  email="not_real@example.com",
                                                  password="lolSecret")
        self.user2 = User.objects.create_superuser(username="TEST_USER2",
                                                  email="not_real2@example.com",
                                                  password="lolSecret2")
        self.num_resources = 10
        pool = Pool.objects.create(name='TEST_POOL')
        self.resources = [Resource.objects.create(pool=pool, name=f"RESOURCE_{x}") for x in
                          range(0, self.num_resources)]
        self.client = self.client_class(
            HTTP_USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:70.0) Gecko/20100101 Firefox/70.0')
        
    def test_list_resources(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('gui:list_resources'))
        self.assertEqual(len(response.context['resources']), Resource.objects.count())

    def test_view_reservation_missing(self):
        response = self.client.get(reverse('gui:view_reservation', kwargs={'resource_pk': 'RESOURCE_1'}))
        self.assertEqual(response.status_code, 302)

    def test_view_reservation_active(self):
        self.resources[1].user = self.user
        self.resources[1].save()
        self.client.force_login(self.user)
        response = self.client.get(reverse('gui:view_reservation', kwargs={'resource_pk': 'RESOURCE_1'}), follow=False)
        self.assertEqual(response.status_code, 200)

    def test_view_reservation_new(self):
        resource_url = reverse('gui:view_reservation', kwargs={'resource_pk': 'RESOURCE_2'})

        self.client.force_login(self.user)
        response = self.client.post(resource_url)
        self.assertEqual(response.status_code, 302)
        # Creating record should redirect to a GET query of the same URL
        self.assertRedirects(expected_url=resource_url, response=response)

    def test_view_reservation_new_duplicate(self):
        self.resources[3].user = self.user2
        self.resources[3].save()

        self.client.force_login(self.user)
        response = self.client.post(reverse('gui:view_reservation', kwargs={'resource_pk': 'RESOURCE_3'}))
        self.assertEqual(response.status_code, 403)

    def test_view_reservation_delete(self):
        self.resources[4].user = self.user
        self.resources[4].save()

        self.client.force_login(self.user)
        response = self.client.post(path=reverse('gui:view_reservation', kwargs={'resource_pk': 'RESOURCE_3'}),
                                    data={'DELETE': 'true'})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(expected_url=reverse('gui:list_resources'), response=response)
