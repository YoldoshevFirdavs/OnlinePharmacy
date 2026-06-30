from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from users.models import CustomUser, DeliveryDriver
from pharmacy.models.medicine import Medicine
from pharmacy.models.medicine import Category
from orders.models import Order, OrderItem, OrderDelivery
from payments.models import Payout
from rest_framework_simplejwt.tokens import RefreshToken

class DriverAuthAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.driver_user = CustomUser.objects.create_user(
            phone_number='+998901112233',
            email='driver@example.com',
            password='driverpassword'
        )
        self.driver_profile = DeliveryDriver.objects.create(
            user=self.driver_user,
            phone='+998901112233',
            vehicle_type='car'
        )
        self.non_driver_user = CustomUser.objects.create_user(
            phone_number='+998904445566',
            email='nondriver@example.com',
            password='nondriverpassword'
        )
        self.login_url = reverse('driver-login')

    def test_driver_login_success_phone(self):
        response = self.client.post(self.login_url, {'phone_number': '+998901112233', 'password': 'driverpassword'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_driver_login_success_email(self):
        response = self.client.post(self.login_url, {'email': 'driver@example.com', 'password': 'driverpassword'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_driver_login_fail_wrong_password(self):
        response = self.client.post(self.login_url, {'phone_number': '+998901112233', 'password': 'wrongpassword'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Unable to log in with provided credentials.', str(response.data))

    def test_driver_login_fail_non_driver_user(self):
        response = self.client.post(self.login_url, {'phone_number': '+998904445566', 'password': 'nondriverpassword'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('User is not a delivery driver.', str(response.data))

    def test_driver_login_fail_missing_credentials(self):
        response = self.client.post(self.login_url, {'password': 'driverpassword'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Must include "phone_number" or "email".', str(response.data))


class DriverOrderAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.customer_user = CustomUser.objects.create_user(
            phone_number='+998901112233',
            email='customer@example.com',
            password='customerpassword'
        )

        self.driver_user = CustomUser.objects.create_user(
            phone_number='+998904445566',
            email='driver@example.com',
            password='driverpassword'
        )
        self.driver_profile = DeliveryDriver.objects.create(
            user=self.driver_user,
            phone='+998904445566',
            vehicle_type='motorbike'
        )

        self.non_driver_user = CustomUser.objects.create_user(
            phone_number='+998907778899',
            email='nondriver@example.com',
            password='nondriverpassword'
        )

        self.category = Category.objects.create(name='Painkillers', slug='painkillers')

        self.medicine1 = Medicine.objects.create(
            name='Paracetamol',
            slug='paracetamol',
            price=10.00,
            stock=100,
            category=self.category,
            short_description='A common painkiller',
            instruction='Take with water'
        )
        self.medicine2 = Medicine.objects.create(
            name='Ibuprofen',
            slug='ibuprofen',
            price=15.00,
            stock=50,
            category=self.category,
            short_description='An anti-inflammatory drug',
            instruction='Take after food'
        )

        self.assigned_order = Order.objects.create(
            customer=self.customer_user,
            driver=self.driver_profile,
            total_price=30.00,
            status='Assigned',
            address='123 Driver St'
        )
        OrderItem.objects.create(order=self.assigned_order, product=self.medicine1, quantity=2, price_at_order=10.00)
        OrderItem.objects.create(order=self.assigned_order, product=self.medicine2, quantity=1, price_at_order=15.00)

        self.accepted_order = Order.objects.create(
            customer=self.customer_user,
            driver=self.driver_profile,
            total_price=20.00,
            status='Accepted',
            address='456 Accepted Ave',
            accepted_at=timezone.now() - timedelta(hours=1)
        )
        OrderItem.objects.create(order=self.accepted_order, product=self.medicine1, quantity=2, price_at_order=10.00)

        self.on_the_way_order = Order.objects.create(
            customer=self.customer_user,
            driver=self.driver_profile,
            total_price=25.00,
            status='On The Way',
            address='789 On The Way Blvd',
            accepted_at=timezone.now() - timedelta(hours=2),
            picked_up_at=timezone.now() - timedelta(hours=1, minutes=30),
            on_the_way_at=timezone.now() - timedelta(minutes=30)
        )
        OrderItem.objects.create(order=self.on_the_way_order, product=self.medicine2, quantity=1, price_at_order=15.00)

        self.unassigned_order = Order.objects.create(
            customer=self.customer_user,
            total_price=50.00,
            status='Pending',
            address='789 Unassigned Rd'
        )
        OrderItem.objects.create(order=self.unassigned_order, product=self.medicine2, quantity=3, price_at_order=15.00)

        self.list_url = reverse('driver-orders-list')
        self.detail_url = lambda pk: reverse('driver-order-detail', kwargs={'pk': pk})
        self.accept_url = lambda pk: reverse('driver-order-accept', kwargs={'pk': pk})
        self.status_url = lambda pk: reverse('driver-order-status-update', kwargs={'pk': pk})
        self.arrival_url = lambda pk: reverse('driver-order-arrival', kwargs={'pk': pk})

    def get_driver_auth_headers(self):
        refresh = RefreshToken.for_user(self.driver_user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def get_non_driver_auth_headers(self):
        refresh = RefreshToken.for_user(self.non_driver_user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def test_driver_can_list_assigned_orders(self):
        headers = self.get_driver_auth_headers()
        response = self.client.get(self.list_url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        order_ids = [order['id'] for order in response.data]
        self.assertIn(self.assigned_order.id, order_ids)
        self.assertIn(self.accepted_order.id, order_ids)
        self.assertIn(self.on_the_way_order.id, order_ids)
        self.assertNotIn(self.unassigned_order.id, order_ids)

    def test_non_driver_cannot_list_orders(self):
        headers = self.get_non_driver_auth_headers()
        response = self.client.get(self.list_url, **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_list_orders(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_driver_can_retrieve_assigned_order_detail(self):
        headers = self.get_driver_auth_headers()
        response = self.client.get(self.detail_url(self.assigned_order.id), **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.assigned_order.id)
        self.assertEqual(response.data['status'], 'Assigned')

    def test_driver_cannot_retrieve_unassigned_order_detail(self):
        headers = self.get_driver_auth_headers()
        response = self.client.get(self.detail_url(self.unassigned_order.id), **headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_driver_cannot_retrieve_order_detail(self):
        headers = self.get_non_driver_auth_headers()
        response = self.client.get(self.detail_url(self.assigned_order.id), **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_can_accept_assigned_order(self):
        headers = self.get_driver_auth_headers()
        response = self.client.post(self.accept_url(self.assigned_order.id), {}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assigned_order.refresh_from_db()
        self.assertEqual(self.assigned_order.status, 'Accepted')
        self.assertIsNotNone(self.assigned_order.accepted_at)

    def test_driver_cannot_accept_already_accepted_order(self):
        headers = self.get_driver_auth_headers()
        response = self.client.post(self.accept_url(self.accepted_order.id), {}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Order cannot be accepted at this stage.", str(response.data))

    def test_driver_cannot_accept_unassigned_order(self):
        headers = self.get_driver_auth_headers()
        response = self.client.post(self.accept_url(self.unassigned_order.id), {}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_driver_can_update_status_to_picked_up(self):
        headers = self.get_driver_auth_headers()
        response = self.client.post(self.status_url(self.accepted_order.id), {'status': 'Picked Up'}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.accepted_order.refresh_from_db()
        self.assertEqual(self.accepted_order.status, 'Picked Up')
        self.assertIsNotNone(self.accepted_order.picked_up_at)

    def test_driver_can_update_status_to_on_the_way(self):
        self.accepted_order.status = 'Picked Up'
        self.accepted_order.picked_up_at = timezone.now()
        self.accepted_order.save()
        headers = self.get_driver_auth_headers()
        response = self.client.post(self.status_url(self.accepted_order.id), {'status': 'On The Way'}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.accepted_order.refresh_from_db()
        self.assertEqual(self.accepted_order.status, 'On The Way')
        self.assertIsNotNone(self.accepted_order.on_the_way_at)

    def test_driver_can_update_status_to_arrived(self):
        self.on_the_way_order.status = 'On The Way'
        self.on_the_way_order.on_the_way_at = timezone.now()
        self.on_the_way_order.save()
        headers = self.get_driver_auth_headers()
        response = self.client.post(self.status_url(self.on_the_way_order.id), {'status': 'Arrived'}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.on_the_way_order.refresh_from_db()
        self.assertEqual(self.on_the_way_order.status, 'Arrived')

    def test_driver_can_update_status_to_delivered(self):
        self.on_the_way_order.status = 'Arrived'
        self.on_the_way_order.save()
        headers = self.get_driver_auth_headers()
        response = self.client.post(self.status_url(self.on_the_way_order.id), {'status': 'Delivered'}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.on_the_way_order.refresh_from_db()
        self.assertEqual(self.on_the_way_order.status, 'Delivered')
        self.assertIsNotNone(self.on_the_way_order.delivered_at)
        self.assertTrue(OrderDelivery.objects.filter(order=self.on_the_way_order).exists())
        order_delivery = OrderDelivery.objects.get(order=self.on_the_way_order)
        self.assertGreater(order_delivery.driver_earnings, 0)

    def test_driver_cannot_skip_status_transition(self):
        headers = self.get_driver_auth_headers()
        response = self.client.post(self.status_url(self.accepted_order.id), {'status': 'Delivered'}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Order cannot be updated to Delivered at its current stage (Accepted).", str(response.data))

    def test_driver_cannot_update_status_of_unassigned_order(self):
        headers = self.get_driver_auth_headers()
        response = self.client.post(self.status_url(self.unassigned_order.id), {'status': 'Picked Up'}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_driver_cannot_update_status_with_invalid_status(self):
        headers = self.get_driver_auth_headers()
        response = self.client.post(self.status_url(self.assigned_order.id), {'status': 'Canceled'}, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid status. Must be one of ['Accepted', 'Picked Up', 'On The Way', 'Arrived', 'Delivered'].", str(response.data))

    def test_driver_can_record_arrival(self):
        headers = self.get_driver_auth_headers()
        arrival_time = timezone.now() - timedelta(minutes=5)
        data = {
            'wait_seconds': 120
        }
        response = self.client.post(self.arrival_url(self.on_the_way_order.id), data, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.on_the_way_order.refresh_from_db()
        self.assertEqual(self.on_the_way_order.status, 'Arrived')
        order_delivery = OrderDelivery.objects.get(order=self.on_the_way_order)
        self.assertEqual(order_delivery.wait_seconds, 120)

    def test_driver_cannot_record_arrival_if_not_on_the_way(self):
        headers = self.get_driver_auth_headers()
        data = {
            'wait_seconds': 60
        }
        response = self.client.post(self.arrival_url(self.accepted_order.id), data, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Order cannot be marked as arrived at this stage.", str(response.data))

    def test_driver_cannot_record_arrival_for_unassigned_order(self):
        headers = self.get_driver_auth_headers()
        data = {
            'wait_seconds': 60
        }
        response = self.client.post(self.arrival_url(self.unassigned_order.id), data, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DriverLocationAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.driver_user = CustomUser.objects.create_user(
            phone_number='+998901112233',
            email='driver@example.com',
            password='driverpassword'
        )
        self.driver_profile = DeliveryDriver.objects.create(
            user=self.driver_user,
            phone='+998901112233',
            vehicle_type='car'
        )
        self.non_driver_user = CustomUser.objects.create_user(
            phone_number='+998904445566',
            email='nondriver@example.com',
            password='nondriverpassword'
        )
        self.location_url = reverse('driver-location-update')

    def get_driver_auth_headers(self):
        refresh = RefreshToken.for_user(self.driver_user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def get_non_driver_auth_headers(self):
        refresh = RefreshToken.for_user(self.non_driver_user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def test_driver_can_update_location(self):
        headers = self.get_driver_auth_headers()
        data = {
            'lat': 41.2995,
            'lng': 69.2401,
        }
        response = self.client.post(self.location_url, data, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.driver_profile.refresh_from_db()
        self.assertEqual(float(self.driver_profile.current_lat), data['lat'])
        self.assertEqual(float(self.driver_profile.current_lng), data['lng'])
        self.assertIsNotNone(self.driver_profile.last_location_update)

    def test_non_driver_cannot_update_location(self):
        headers = self.get_non_driver_auth_headers()
        data = {
            'lat': 41.2995,
            'lng': 69.2401,
        }
        response = self.client.post(self.location_url, data, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_update_location(self):
        data = {
            'lat': 41.2995,
            'lng': 69.2401,
        }
        response = self.client.post(self.location_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_location_invalid_data(self):
        headers = self.get_driver_auth_headers()
        data = {
            'lat': 'invalid',
            'lng': 69.2401,
        }
        response = self.client.post(self.location_url, data, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('A valid number is required.', str(response.data))


class DriverPayoutAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.driver_user = CustomUser.objects.create_user(
            phone_number='+998901112233',
            email='driver@example.com',
            password='driverpassword'
        )
        self.driver_profile = DeliveryDriver.objects.create(
            user=self.driver_user,
            phone='+998901112233',
            vehicle_type='car'
        )
        self.non_driver_user = CustomUser.objects.create_user(
            phone_number='+998904445566',
            email='nondriver@example.com',
            password='nondriverpassword'
        )

        self.payout1 = Payout.objects.create(
            driver=self.driver_profile,
            amount_gross=100.00,
            tax_amount=10.00,
            commission_amount=0.00,
            net_amount=90.00,
            status='Completed'
        )
        self.payout2 = Payout.objects.create(
            driver=self.driver_profile,
            amount_gross=50.00,
            tax_amount=5.00,
            commission_amount=0.00,
            net_amount=45.00,
            status='Pending'
        )

        self.other_driver_user = CustomUser.objects.create_user(
            phone_number='+998907778899',
            email='otherdriver@example.com',
            password='otherdriverpassword'
        )
        self.other_driver_profile = DeliveryDriver.objects.create(
            user=self.other_driver_user,
            phone='+998907778899',
            vehicle_type='bike'
        )
        self.other_payout = Payout.objects.create(
            driver=self.other_driver_profile,
            amount_gross=200.00,
            tax_amount=20.00,
            commission_amount=0.00,
            net_amount=180.00,
            status='Completed'
        )

        self.list_url = reverse('driver-payouts-list')

    def get_driver_auth_headers(self):
        refresh = RefreshToken.for_user(self.driver_user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def get_non_driver_auth_headers(self):
        refresh = RefreshToken.for_user(self.non_driver_user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def test_driver_can_list_their_payouts(self):
        headers = self.get_driver_auth_headers()
        response = self.client.get(self.list_url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        payout_ids = [payout['id'] for payout in response.data]
        self.assertIn(self.payout1.id, payout_ids)
        self.assertIn(self.payout2.id, payout_ids)
        self.assertNotIn(self.other_payout.id, payout_ids)

    def test_non_driver_cannot_list_payouts(self):
        headers = self.get_non_driver_auth_headers()
        response = self.client.get(self.list_url, **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_list_payouts(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)