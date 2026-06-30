from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from users.models import CustomUser, Deliverer, SalaryRecord, PayrollStats
from users.tasks import calculate_monthly_payroll
from django.conf import settings

class PayrollCalculationTests(TestCase):
    def setUp(self):
        self.user1 = CustomUser.objects.create_user(email="deliverer1@example.com", password="testpassword", role='deliverer')
        self.user2 = CustomUser.objects.create_user(email="deliverer2@example.com", password="testpassword", role='deliverer')

        self.deliverer1 = Deliverer.objects.create(
            user=self.user1,
            phone_number="+998901112233",
            status='active',
            rate_per_hour=20.00,
            stripe_account_id="acct_12345"
        )
        self.deliverer2 = Deliverer.objects.create(
            user=self.user2,
            phone_number="+998904445566",
            status='active',
            rate_per_hour=25.00,
            stripe_account_id="acct_67890"
        )

        # Set default payroll settings for tests
        settings.PAYROLL_RATE_PER_HOUR = 15.00
        settings.PAYROLL_TAX_RATE = 0.10

    @patch('users.tasks.logger')
    @patch('users.tasks.stripe') # Mock Stripe API calls
    def test_calculate_monthly_payroll_success(self, mock_stripe, mock_logger):
        # Simulate running the task for the previous month
        # Assuming today is 2023-02-01, so payroll is for 2023-01
        with patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = timezone.datetime(2023, 2, 1, tzinfo=timezone.utc)
            
            # Mock Stripe Payout creation
            mock_stripe.Payout.create.return_value = MagicMock(id="pay_stripe123")

            calculate_monthly_payroll()

            # Check SalaryRecord for deliverer1
            salary1 = SalaryRecord.objects.get(deliverer=self.deliverer1, period_start=date(2023, 1, 1), period_end=date(2023, 1, 31))
            self.assertEqual(salary1.hours_worked, 160)
            self.assertEqual(salary1.rate_per_hour, 20.00)
            self.assertEqual(salary1.gross_amount, 3200.00) # 160 * 20
            self.assertEqual(salary1.taxes_amount, 320.00) # 3200 * 0.10
            self.assertEqual(salary1.net_amount, 2880.00) # 3200 - 320
            self.assertEqual(salary1.status, 'paid')
            self.assertIsNotNone(salary1.stripe_payment_id)

            # Check SalaryRecord for deliverer2
            salary2 = SalaryRecord.objects.get(deliverer=self.deliverer2, period_start=date(2023, 1, 1), period_end=date(2023, 1, 31))
            self.assertEqual(salary2.hours_worked, 160)
            self.assertEqual(salary2.rate_per_hour, 25.00)
            self.assertEqual(salary2.gross_amount, 4000.00) # 160 * 25
            self.assertEqual(salary2.taxes_amount, 400.00) # 4000 * 0.10
            self.assertEqual(salary2.net_amount, 3600.00) # 4000 - 400
            self.assertEqual(salary2.status, 'paid')
            self.assertIsNotNone(salary2.stripe_payment_id)

            # Check PayrollStats
            payroll_stats = PayrollStats.objects.get(month=1, year=2023)
            self.assertEqual(payroll_stats.total_gross, 7200.00) # 3200 + 4000
            self.assertEqual(payroll_stats.total_net, 6480.00) # 2880 + 3600
            self.assertEqual(payroll_stats.total_fees, 720.00) # 320 + 400
            self.assertEqual(payroll_stats.total_payouts, 6480.00) # 2880 + 3600

            # Ensure Stripe payout was called for each deliverer
            self.assertEqual(mock_stripe.Payout.create.call_count, 2)
            mock_stripe.Payout.create.assert_any_call(
                amount=int(2880.00 * 100),
                currency='usd', # Assuming default currency
                destination=self.deliverer1.stripe_account_id,
                idempotency_key=f"payroll_payout_{salary1.id}",
            )
            mock_stripe.Payout.create.assert_any_call(
                amount=int(3600.00 * 100),
                currency='usd', # Assuming default currency
                destination=self.deliverer2.stripe_account_id,
                idempotency_key=f"payroll_payout_{salary2.id}",
            )

    @patch('users.tasks.logger')
    @patch('users.tasks.stripe')
    def test_calculate_monthly_payroll_no_active_deliverers(self, mock_stripe, mock_logger):
        Deliverer.objects.all().update(status='suspended') # Suspend all deliverers
        with patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = timezone.datetime(2023, 2, 1, tzinfo=timezone.utc)
            calculate_monthly_payroll()
            self.assertEqual(SalaryRecord.objects.count(), 0)
            self.assertEqual(PayrollStats.objects.count(), 0)
            mock_stripe.Payout.create.assert_not_called()
            mock_logger.info.assert_any_call("No active deliverers found for payroll calculation.")

    @patch('users.tasks.logger')
    @patch('users.tasks.stripe')
    def test_calculate_monthly_payroll_stripe_failure(self, mock_stripe, mock_logger):
        mock_stripe.Payout.create.side_effect = Exception("Stripe API Error")
        with patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = timezone.datetime(2023, 2, 1, tzinfo=timezone.utc)
            calculate_monthly_payroll()

            salary1 = SalaryRecord.objects.get(deliverer=self.deliverer1, period_start=date(2023, 1, 1), period_end=date(2023, 1, 31))
            self.assertEqual(salary1.status, 'failed')
            self.assertIsNone(salary1.stripe_payment_id)

            salary2 = SalaryRecord.objects.get(deliverer=self.deliverer2, period_start=date(2023, 1, 1), period_end=date(2023, 1, 31))
            self.assertEqual(salary2.status, 'failed')
            self.assertIsNone(salary2.stripe_payment_id)

            self.assertEqual(mock_stripe.Payout.create.call_count, 2) # Still attempts for both
            mock_logger.error.assert_any_call(
                "Stripe payout failed for deliverer %s (ID: %s): %s",
                self.deliverer1.user.email, self.deliverer1.id, MagicMock()
            )
            mock_logger.error.assert_any_call(
                "Stripe payout failed for deliverer %s (ID: %s): %s",
                self.deliverer2.user.email, self.deliverer2.id, MagicMock()
            )

    @patch('users.tasks.logger')
    @patch('users.tasks.stripe')
    def test_calculate_monthly_payroll_already_processed(self, mock_stripe, mock_logger):
        # Create a dummy PayrollStats entry for the month
        PayrollStats.objects.create(
            month=1, year=2023,
            total_gross=100.00, total_net=90.00, total_fees=10.00, total_payouts=90.00
        )
        with patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = timezone.datetime(2023, 2, 1, tzinfo=timezone.utc)
            calculate_monthly_payroll()
            self.assertEqual(SalaryRecord.objects.count(), 0) # No new records should be created
            mock_stripe.Payout.create.assert_not_called()
            mock_logger.info.assert_any_call("Payroll for 1/2023 already processed. Skipping.")