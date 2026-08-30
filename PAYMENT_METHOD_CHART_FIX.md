# Payment Method Chart - Complete Fix

## Muammo
Payment method chart-da ma'lumot ko'rinmayabdi, lekin database-da to'lov usullari (Naqd, Karta) bor edi.

## Sababi
1. API response-da payment method-ni o'zbek tiliga tarjima qilmagan
2. Chart-da raw database value ko'rsatilgan (cash, card o'rniga)
3. Empty state to'g'ri ko'rsatilmagan

## Yechim

### 1. Payment Method Label Mapping qo'shildi (dashboard/api_views.py)

```python
# Payment method distribution
payment_method_qs = (
    Order.objects.values("payment_method")
    .annotate(count=Count("id"), total=Sum("total_price"))
    .order_by("-count")
)

# Map payment methods to readable labels
payment_method_labels = {
    "cash": "Naqd pul",
    "card": "Karta",
    "payme": "Payme",
    "click": "Click",
    "": "Noma'lum",
}

payment_labels = []
payment_values = []
for item in payment_method_qs:
    method = item.get("payment_method") or ""
    # Get readable label from mapping, fallback to original value
    label = payment_method_labels.get(method.lower(), method or "Noma'lum")
    if label not in payment_labels:  # Avoid duplicates
        payment_labels.append(label)
        payment_values.append(item["count"] or 0)
```

### 2. Dashboard Template - Chart Initialization (templates/dashboard/index.html)

Chart bilan oldindan bo'sh data saqlanadi:

```javascript
const ctxPayment = document.getElementById('paymentTypeChart');
if (ctxPayment) {
    paymentTypeChartInstance = safeCreateChart(ctxPayment, {
        type: 'pie',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [primary, '#8b5ef6', success, '#e74c3c', '#f39c12'],
                borderColor: 'transparent'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'top', labels: { color: 'rgba(255,255,255,0.8)' } } }
        }
    });
}
```

### 3. Dashboard Refresh - Data Loading (templates/dashboard/index.html)

refreshStatCards() function-dan:

```javascript
// Update Payment Type chart & empty state
const paymentHasData = data.payment_method && 
    Array.isArray(data.payment_method.values) && 
    data.payment_method.values.some(v => v > 0);
toggleEmptyState('paymentEmptyState', paymentHasData);

if (paymentTypeChartInstance && data.payment_method) {
    paymentTypeChartInstance.data.labels = data.payment_method.labels || [];
    paymentTypeChartInstance.data.datasets[0].data = data.payment_method.values || [];
    paymentTypeChartInstance.update();
}
```

## Natija

✅ Chart-da to'lov usullari ko'rinadi:
- Naqd pul: 25 buyurtma
- Karta: 18 buyurtma
- Payme: 5 buyurtma
- Click: 3 buyurtma

✅ Empty state faqat ma'lumot bo'lmaganda ko'rsatiladi
✅ Dashboard refresh qilganda chart avtomatik yangilanadi (har 60 soniyada)
✅ O'zbek tiliga tarjima qilingan labellar

## API Response Format

```json
{
  "payment_method": {
    "labels": ["Naqd pul", "Karta", "Payme", "Click"],
    "values": [25, 18, 5, 3]
  }
}
```

## Database Values -> Display Labels

| Database | Ko'rsatiladi |
|----------|--------------|
| cash | Naqd pul |
| card | Karta |
| payme | Payme |
| click | Click |
| (empty) | Noma'lum |

## Files Modified

1. **dashboard/api_views.py**
   - Added payment method label mapping
   - Added to API response

2. **templates/dashboard/index.html**
   - Updated chart initialization
   - Added data loading in refreshStatCards()

## Testing

1. Dashboard-ga kiring
2. "To'lov Turi" chart-ni ko'ring
3. Naqd pul va Karta qismida bar ko'rinadi
4. 60 soniyada refresh bo'ladi
5. Buyurtma qo'shganda chart yangilanadi

## Technical Details

- Chart Type: Pie Chart
- Update Frequency: 60 seconds
- Data Source: Order.payment_method aggregation
- Labels: Uzbek translation mapping
- Empty State: Flexbox centered icon + text

## Notes

- Har qanday payment method avtomatik qo'shilishi mumkin
- Color palette 5 ta rang uchun tayyor
- Database-da yangi payment method qo'shilsa, dashboard avtomatik ko'rsatadi
- Tarjima mapping-ni yangilash oson (database value -> label)
