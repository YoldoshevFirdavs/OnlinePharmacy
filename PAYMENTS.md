# Payment Processing & Billing

## Table of Contents
1. [Overview](#overview)
2. [Payment Methods](#payment-methods)
3. [Stripe Integration](#stripe-integration)
4. [Checkout Flow](#checkout-flow)
5. [Order Payments](#order-payments)
6. [Delivery Driver Salaries](#delivery-driver-salaries)
7. [Refunds & Disputes](#refunds--disputes)
8. [Payment Webhooks](#payment-webhooks)
9. [Testing & Debugging](#testing--debugging)
10. [Security Best Practices](#security-best-practices)

---

## Overview

OnlinePharmacy supports dual payment methods:

1. **Cash on Delivery (CoD)** — Pay after receipt
2. **Card Payment** — Online via Stripe

The system tracks customer payments and driver salary calculations.

### Key Models

```python
# billing/models.py
class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [("cash", "Naqd pul"), ("card", "Karta")]
    
    order = ForeignKey(Order, related_name="payments", on_delete=CASCADE)
    stripe_charge_id = CharField(max_length=70, blank=True, null=True)
    amount = DecimalField(max_digits=10, decimal_places=2)
    payment_method = CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="cash")
    status = CharField(max_length=20, default="pending")  # pending, succeeded, failed
    created_at = DateTimeField(auto_now_add=True)

# payments/models.py
class Salary(models.Model):
    STATUS_CHOICES = [("Pending", "Pending"), ("Paid", "Paid")]
    
    driver = ForeignKey(DeliveryDriver, on_delete=CASCADE, related_name="salaries")
    amount = DecimalField(max_digits=10, decimal_places=2)
    status = CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    period_start = DateField(null=True, blank=True)
    period_end = DateField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    paid_at = DateTimeField(null=True, blank=True)
```

---

## Payment Methods

### Cash on Delivery

**Flow:**
1. User creates order
2. Selects "Naqd pul" (Cash) payment
3. Order status: "Pending"
4. Driver delivers and collects payment
5. Order status: "Delivered"

**Implementation:**

```python
# orders/models.py
class Order(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Processing", "Processing"),
        ("Delivered", "Delivered"),
        ("Canceled", "Canceled"),
    ]
    
    user = ForeignKey(CustomUser, on_delete=CASCADE, related_name="orders")
    total_price = DecimalField(max_digits=12, decimal_places=2)
    status = CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    payment_method = CharField(
        max_length=20,
        choices=[("cash", "Naqd pul"), ("card", "Karta")],
        default="cash"
    )
    address = TextField(blank=True, null=True)
    phone_number = CharField(max_length=20, blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)
    delivered_at = DateTimeField(null=True, blank=True)
```

**Endpoint:**

```python
# POST /api/v1/orders/
{
    "address": "Tashkent, Mirzo Ulugbek district",
    "phone_number": "+998901234567",
    "payment_method": "cash",  # or "card"
    "items": [
        {
            "product_id": 1,
            "quantity": 2
        }
    ]
}
```

### Card Payment (Stripe)

**Flow:**
1. User creates order with `payment_method: "card"`
2. Frontend calls POST `/api/v1/payments/checkout-session/`
3. Backend creates Stripe Checkout Session
4. User redirected to Stripe payment page
5. After payment → webhook updates order status

**Advantages:**
- Secure PCI-compliant payment
- Automatic fraud detection
- Instant payment confirmation
- Dispute resolution

---

## Stripe Integration

### Configuration

**Setup Stripe account:**

1. Create account at [stripe.com](https://stripe.com)
2. Get API keys from Dashboard → Developers → API keys

**Environment variables:**

```env
# .env (development)
STRIPE_SECRET_KEY=sk_test_51...
STRIPE_PUBLIC_KEY=pk_test_51...

# .env.prod (production - use live keys)
STRIPE_SECRET_KEY=sk_live_... 
STRIPE_PUBLIC_KEY=pk_live_...
```

**Django settings:**

```python
# config/settings.py
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLIC_KEY", "")

# Stripe initialization
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
```

---

## Checkout Flow

### Step 1: Create Order

**POST /api/v1/orders/**

```python
# Frontend (JavaScript/React)
const response = await fetch('/api/v1/orders/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        address: "User address",
        phone_number: "+998901234567",
        payment_method: "card",
        items: [
            { product_id: 1, quantity: 2 },
            { product_id: 2, quantity: 1 }
        ]
    })
});

const order = await response.json();
console.log("Order created:", order.id);
```

### Step 2: Create Checkout Session

**POST /api/v1/payments/checkout-session/**

```python
# Backend: billing/views.py
class StripeCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {"error": "Buyurtma topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Build line items from order items
        line_items = []
        for oi in order.order_items.select_related("product").all():
            unit_price = int(oi.price_at_order * 100)  # Stripe uses cents
            
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "unit_amount": unit_price,
                    "product_data": {
                        "name": oi.product.name,
                    },
                },
                "quantity": oi.quantity,
            })

        # Create Stripe session
        host = request.build_absolute_uri("/")
        success_url = f"{host}order/?payment=success&order_id={order.id}"
        cancel_url = f"{host}order/?payment=cancelled&order_id={order.id}"

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"order_id": str(order.id)},
        )

        return Response({
            "session_id": checkout_session.id,
            "redirect_url": checkout_session.url
        })
```

**Frontend redirect:**

```javascript
const response = await fetch('/api/v1/payments/checkout-session/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({ order_id: orderId })
});

const { redirect_url } = await response.json();

// Redirect to Stripe Checkout
window.location.href = redirect_url;
```

### Step 3: Payment & Success

After payment, Stripe redirects user to success URL:
```
http://localhost:8000/order/?payment=success&order_id=123
```

### Step 4: Webhook Confirmation

Stripe webhook confirms payment and updates order:

```python
# POST /api/v1/payments/webhook/
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return Response({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError:
        return Response({"error": "Invalid signature"}, status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session['metadata']['order_id']
        
        order = Order.objects.get(id=order_id)
        order.status = "Paid"
        order.save()
        
        # Create payment record
        Payment.objects.create(
            order=order,
            stripe_charge_id=session.get('payment_intent'),
            amount=order.total_price,
            payment_method="card",
            status="succeeded"
        )

    return Response({"status": "success"})
```

**Configure webhook in Stripe Dashboard:**
- Endpoint URL: `https://yourdomain.com/api/v1/payments/webhook/`
- Events: `checkout.session.completed`, `charge.refunded`

---

## Order Payments

### Payment Status Flow

```
User Creates Order
        ↓
  [ Cash ] ──→ Pending (Driver collects on delivery)
        ↓                ↓
  [ Card ] ──→ Stripe Checkout ──→ Payment Confirmation ──→ Processing
        ↓                                                      ↓
  Success URL ──→ Order Status: "Paid"                   Delivered
        ↓
  Webhook Updates Database
```

### Tracking Payments

**Get payment history:**

```python
# GET /api/v1/orders/{order_id}/payments/
class OrderPaymentsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_id):
        order = Order.objects.get(id=order_id, user=request.user)
        payments = order.payments.all()
        
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)
```

**Response:**

```json
[
  {
    "id": 1,
    "order": 123,
    "stripe_charge_id": "ch_1A8OWF...",
    "amount": "49.99",
    "payment_method": "card",
    "status": "succeeded",
    "created_at": "2026-08-24T10:30:00Z"
  }
]
```

---

## Delivery Driver Salaries

### Salary Calculation

Drivers earn based on:
- Number of deliveries
- Base rate per delivery
- Bonuses for performance

**Configuration:**

```python
# config/settings.py
PAYROLL_RATE_PER_HOUR = float(os.getenv("PAYROLL_RATE_PER_HOUR", 20.0))  # USD per hour
PAYROLL_TAX_RATE = float(os.getenv("PAYROLL_TAX_RATE", 0.15))  # 15% tax
```

**Salary Model:**

```python
class Salary(models.Model):
    STATUS_CHOICES = [("Pending", "Pending"), ("Paid", "Paid")]
    
    driver = ForeignKey(DeliveryDriver, on_delete=CASCADE, related_name="salaries")
    amount = DecimalField(max_digits=10, decimal_places=2)
    status = CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    period_start = DateField(null=True, blank=True)  # e.g., 2026-08-01
    period_end = DateField(null=True, blank=True)    # e.g., 2026-08-31
    created_at = DateTimeField(auto_now_add=True)
    paid_at = DateTimeField(null=True, blank=True)
```

### Calculate Salary (Admin Function)

```python
from datetime import date, timedelta
from django.utils import timezone
from decimal import Decimal

def calculate_monthly_salary(driver, year, month):
    """Calculate salary for driver for given month"""
    from calendar import monthrange
    
    # Get date range
    days_in_month = monthrange(year, month)[1]
    period_start = date(year, month, 1)
    period_end = date(year, month, days_in_month)
    
    # Count deliveries
    deliveries = DeliveryOrder.objects.filter(
        driver=driver,
        assigned_at__date__gte=period_start,
        assigned_at__date__lte=period_end,
        status="completed"
    ).count()
    
    # Calculate amount (e.g., $2 per delivery)
    amount_per_delivery = Decimal("2.00")
    gross_amount = Decimal(deliveries) * amount_per_delivery
    
    # Apply tax
    tax = gross_amount * Decimal(settings.PAYROLL_TAX_RATE)
    net_amount = gross_amount - tax
    
    # Create salary record
    salary = Salary.objects.create(
        driver=driver,
        amount=net_amount,
        period_start=period_start,
        period_end=period_end,
        status="Pending"
    )
    
    return salary

# Usage
from users.models import DeliveryDriver
driver = DeliveryDriver.objects.first()
salary = calculate_monthly_salary(driver, 2026, 8)
print(f"Salary: ${salary.amount} (Pending)")
```

### Pay Salary

```python
def pay_driver_salary(salary_id):
    """Mark salary as paid (admin function)"""
    salary = Salary.objects.get(id=salary_id)
    salary.status = "Paid"
    salary.paid_at = timezone.now()
    salary.save()
    
    # TODO: Integrate with bank transfer API (e.g., Wise, PayPal)
    # send_payment_to_driver_bank_account(salary.driver, salary.amount)
    
    return salary
```

---

## Refunds & Disputes

### Refund Process

**1. Customer Requests Refund**

```python
# POST /api/v1/orders/{order_id}/refund/
class OrderRefundView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, order_id):
        order = Order.objects.get(id=order_id, user=request.user)
        
        if order.status not in ["Delivered", "Paid"]:
            return Response(
                {"error": "Only delivered orders can be refunded"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get("reason")
        
        # Process refund
        try:
            refund = stripe.Refund.create(
                charge=order.payments.first().stripe_charge_id,
                reason=reason  # "requested_by_customer"
            )
            
            order.status = "Returned"
            order.save()
            
            # Log refund
            AuditLog.objects.create(
                user=request.user,
                action="refund_requested",
                target_type="order",
                target_id=order.id,
                meta={"reason": reason}
            )
            
            return Response({"refund_id": refund.id})
        except stripe.error.InvalidRequestError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
```

**2. Admin Approves Refund**

```python
# PATCH /api/v1/admin/refunds/{refund_id}/approve/
@permission_classes([IsAdminUser])
def approve_refund(request, refund_id):
    # Confirm refund in Stripe
    refund = stripe.Refund.retrieve(refund_id)
    if refund.status == "succeeded":
        # Refund confirmed
        return Response({"status": "refund_confirmed"})
```

### Dispute Handling

**Stripe Disputes (Chargebacks):**

```python
# Webhook handler for disputes
if event['type'] == 'charge.dispute.created':
    dispute = event['data']['object']
    charge_id = dispute['charge']
    
    # Find order
    payment = Payment.objects.get(stripe_charge_id=charge_id)
    order = payment.order
    
    # Notify admin
    send_notification_to_admin(
        f"Chargeback dispute for order #{order.id}: {dispute['reason']}"
    )
    
    # Log dispute
    AuditLog.objects.create(
        action="dispute_created",
        target_type="order",
        target_id=order.id,
        meta={"dispute_id": dispute['id'], "reason": dispute['reason']}
    )
```

---

## Payment Webhooks

### Webhook Setup

**Register webhook endpoint:**

```python
# config/urls.py
from billing.views import stripe_webhook

urlpatterns = [
    # ...
    path('api/v1/payments/webhook/', stripe_webhook, name='stripe-webhook'),
]
```

**Configure in Stripe Dashboard:**

1. Go to Developers → Webhooks
2. Add endpoint: `https://yourdomain.com/api/v1/payments/webhook/`
3. Select events:
   - `checkout.session.completed`
   - `charge.refunded`
   - `charge.dispute.created`
   - `charge.failed`

**Get webhook signing secret:**

```env
STRIPE_WEBHOOK_SECRET=whsec_test_...
```

### Webhook Handler

```python
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import stripe

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        return JsonResponse({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        return JsonResponse({"error": "Invalid signature"}, status=400)

    # Handle events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_completed(session)
    
    elif event['type'] == 'charge.refunded':
        charge = event['data']['object']
        handle_charge_refunded(charge)
    
    elif event['type'] == 'charge.failed':
        charge = event['data']['object']
        handle_charge_failed(charge)
    
    elif event['type'] == 'charge.dispute.created':
        dispute = event['data']['object']
        handle_dispute_created(dispute)

    return JsonResponse({"status": "success"})

def handle_checkout_completed(session):
    """Update order to Paid"""
    order_id = session['metadata']['order_id']
    order = Order.objects.get(id=order_id)
    order.status = "Paid"
    order.save()
    
    Payment.objects.create(
        order=order,
        stripe_charge_id=session.get('payment_intent'),
        amount=order.total_price,
        payment_method="card",
        status="succeeded"
    )
    logger.info(f"Order {order_id} payment succeeded")

def handle_charge_refunded(charge):
    """Handle refund"""
    payment = Payment.objects.get(stripe_charge_id=charge['id'])
    order = payment.order
    order.status = "Returned"
    order.save()
    logger.info(f"Order {order.id} refunded")

def handle_charge_failed(charge):
    """Handle payment failure"""
    payment = Payment.objects.get(stripe_charge_id=charge['id'])
    payment.status = "failed"
    payment.save()
    logger.error(f"Payment failed for order {payment.order.id}: {charge['failure_message']}")

def handle_dispute_created(dispute):
    """Handle chargeback"""
    payment = Payment.objects.get(stripe_charge_id=dispute['charge'])
    order = payment.order
    logger.warning(f"Dispute created for order {order.id}: {dispute['reason']}")
```

---

## Testing & Debugging

### Test Card Numbers

Use these Stripe test cards:

| Number | CVC | ZIP | Outcome |
|--------|-----|-----|---------|
| 4242 4242 4242 4242 | Any 3 digits | Any 5 digits | Succeeds |
| 4000 0000 0000 0002 | Any | Any | Declined |
| 4000 0000 0000 9995 | Any | Any | Declined (insufficient funds) |
| 5555 5555 5555 4444 | Any | Any | Succeeds (Mastercard) |
| 378282246310005 | Any | Any | Succeeds (Amex) |

### Local Testing

```bash
# Test webhook locally (install Stripe CLI)
stripe listen --forward-to localhost:8000/api/v1/payments/webhook/

# Trigger test event
stripe trigger checkout.session.completed
```

### Debug Logs

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Creating checkout session for order {order.id}")
logger.debug(f"Line items: {line_items}")
logger.error(f"Stripe error: {str(e)}")
```

### Check Stripe Events Dashboard

1. Go to Stripe Dashboard
2. Developers → Events
3. View all webhook calls and responses

---

## Security Best Practices

### 1. Never Log Sensitive Data

```python
# ❌ BAD
logger.info(f"Card token: {stripe_token}")

# ✅ GOOD
logger.info(f"Processing payment for order {order_id}")
```

### 2. Validate Webhook Signatures

Always verify Stripe webhook signatures:

```python
try:
    event = stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
except stripe.error.SignatureVerificationError:
    return JsonResponse({"error": "Invalid signature"}, status=403)
```

### 3. Use HTTPS Only

```python
if not request.is_secure() and not DEBUG:
    return Response({"error": "HTTPS required"}, status=403)
```

### 4. Implement Rate Limiting

```python
from rest_framework.throttling import UserRateThrottle

class PaymentThrottle(UserRateThrottle):
    scope = "payments"
    rate = "10/hour"  # Max 10 payment attempts per hour

class CheckoutSessionView(APIView):
    throttle_classes = [PaymentThrottle]
```

### 5. Validate Order Before Processing

```python
def validate_order(order_id, user):
    """Ensure order belongs to user and is eligible for payment"""
    order = Order.objects.get(id=order_id, user=user)
    
    if order.status == "Paid":
        raise ValueError("Order already paid")
    
    if not order.order_items.exists():
        raise ValueError("Order has no items")
    
    return order
```

### 6. Handle PCI Compliance

- **Never** store raw card data
- Always use Stripe tokens
- Use HTTPS (TLS 1.2+)
- Implement 3D Secure for enhanced security

```python
# ✅ Use Stripe tokenization (frontend)
// JavaScript
stripe.createToken(cardElement).then(function(result) {
    if (result.error) {
        // Handle error
    } else {
        // Send token to backend
        fetch('/api/v1/payments/charge/', {
            body: JSON.stringify({ stripeToken: result.token.id })
        });
    }
});
```

---

## Environment Configuration

### Development (.env)

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_test_...
PAYROLL_RATE_PER_HOUR=20.0
PAYROLL_TAX_RATE=0.15
DEBUG=True
```

### Production (.env.prod)

```env
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_live_...
PAYROLL_RATE_PER_HOUR=20.0
PAYROLL_TAX_RATE=0.15
DEBUG=False
SECURE_SSL_REDIRECT=True
```

---

## Summary

OnlinePharmacy payment system:

- **Dual payment methods:** Cash & Stripe card
- **Secure checkout:** Stripe Checkout Sessions
- **Webhook handling:** Automatic status updates
- **Refund support:** Customer-initiated and admin-approved
- **Driver payroll:** Monthly salary calculations
- **Audit logging:** All payment actions tracked
- **PCI compliant:** No raw card data storage

Key files:
- `billing/models.py` — Payment model
- `billing/views.py` — Checkout & webhook handlers
- `payments/models.py` — Driver salary tracking
- `orders/models.py` — Order payment states
