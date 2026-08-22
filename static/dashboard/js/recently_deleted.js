(function(){
  // Minimal JS to fetch deleted items and perform undo via API
  function getCsrf() {
    const cookie = document.cookie.split(';').map(c=>c.trim()).find(c=>c.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : null;
  }

  function fmtDate(iso) {
    try { return new Date(iso).toLocaleString(); } catch(e) { return iso; }
  }

  async function fetchDeletedItems() {
    const api = document.getElementById('deletedItemsApi').value;
    const tb = document.querySelector('#recentlyDeletedTable tbody');
    tb.innerHTML = '<tr><td colspan="6">Loading...</td></tr>';
    try {
      const res = await fetch(api, { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Fetch failed');
      const json = await res.json();
      renderRows(json.results || []);
    } catch (err) {
      tb.innerHTML = '<tr><td colspan="6">Error loading items</td></tr>';
      console.error(err);
    }
  }

  function renderRows(items) {
    const tb = document.querySelector('#recentlyDeletedTable tbody');
    if (!items.length) { tb.innerHTML = '<tr><td colspan="6">No recent deletions</td></tr>'; return; }
    tb.innerHTML = '';
    items.forEach(it => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${it.item_type}</td>
        <td>${it.item_id}</td>
        <td>${it.item_name || ''}</td>
        <td>${fmtDate(it.deleted_at)}</td>
        <td>${it.deleted_by ? (it.deleted_by.full_name || it.deleted_by.email) : ''}</td>
        <td>
          ${it.item_type === 'order' ? `<a class="btn btn-sm btn-outline-primary" href="/dashboard/admin/orders/${it.item_id}/view/">View</a>` : ''}
          <button class="btn btn-sm btn-warning ml-2 undo-btn" data-type="${it.item_type}" data-id="${it.item_id}">Undo</button>
        </td>
      `;
      tb.appendChild(tr);
    });

    document.querySelectorAll('.undo-btn').forEach(btn => {
      btn.addEventListener('click', onUndo);
    });
  }

  async function onUndo(e) {
    const btn = e.currentTarget;
    const itemType = btn.getAttribute('data-type');
    const itemId = btn.getAttribute('data-id');
    if (!confirm('Are you sure you want to restore this item? This is allowed only within 24 hours.')) return;
    const api = document.getElementById('undoApi').value;
    const payload = { action: 'undo', item_type: itemType, item_id: itemId };
    try {
      const res = await fetch(api, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrf()
        },
        body: JSON.stringify(payload)
      });
      const json = await res.json();
      if (res.ok && json.success) {
        // remove row
        btn.closest('tr').remove();
        alert('Restored');
      } else {
        alert(json.message || 'Undo failed');
      }
    } catch (err) {
      console.error(err);
      alert('Undo request failed');
    }
  }

  // Init
  document.addEventListener('DOMContentLoaded', fetchDeletedItems);
})();
