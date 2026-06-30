import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_verify_otp_missing_fields_returns_400():
    client = APIClient()
    url = reverse('verify-otp')
    resp = client.post(url, {}, format='json')
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    # response should indicate missing fields
    assert 'session_id' in resp.data or 'detail' in resp.data
