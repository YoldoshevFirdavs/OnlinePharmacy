(function(){
  let currentUrl = null;

  function getCsrf() {
    const cookie = document.cookie.split(';').map(c=>c.trim()).find(c=>c.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : null;
  }

  function fmtDate(iso) {
    try { return new Date(iso).toLocaleString(); } catch(e) { return iso; }
  }

  async function fetchDeletedItems(url) {
    const defaultApi = document.getElementById('deletedItemsApi').value;
    const fetchApi = url || defaultApi;
    currentUrl = fetchApi;
    const tb = document.querySelector('#recentlyDeletedTable tbody');
    tb.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 2rem;">Loading...</td></tr>';
    try {
      const res = await fetch(fetchApi, { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Fetch failed');
      const json = await res.json();
      renderRows(json.results || []);
      renderPagination(json);
    } catch (err) {
      tb.innerHTML = '<tr><td colspan="6" style="text-align:center; color: var(--clr-error, #e74c3c); padding: 2rem;">Error loading items</td></tr>';
      console.error(err);
    }
  }

  function renderRows(items) {
    const tb = document.querySelector('#recentlyDeletedTable tbody');
    if (!items || !items.length) {
      tb.innerHTML = `
        <tr class="data-table__empty">
          <td colspan="6">
            <i class="fa-solid fa-inbox"></i>
            <span>No recent deletions</span>
          </td>
        </tr>`;
      return;
    }
    tb.innerHTML = '';
    items.forEach(it => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><span class="badge badge--pill badge--secondary">${it.item_type}</span></td>
        <td>#${it.item_id}</td>
        <td><strong>${it.item_name || ''}</strong></td>
        <td>${fmtDate(it.deleted_at)}</td>
        <td>${it.deleted_by ? (it.deleted_by.full_name || it.deleted_by.email) : 'System/Admin'}</td>
        <td>
          ${it.item_type === 'order' ? `<a class="btn btn-sm btn-outline-primary" href="/dashboard/admin/orders/${it.item_id}/view/"><i class="fa-solid fa-eye"></i> View</a>` : ''}
          <button class="btn btn-sm btn-warning undo-btn" style="margin-left: 4px;" data-type="${it.item_type}" data-id="${it.item_id}">
            <i class="fa-solid fa-rotate-left"></i> Undo
          </button>
        </td>
      `;
      tb.appendChild(tr);
    });

    document.querySelectorAll('.undo-btn').forEach(btn => {
      btn.addEventListener('click', onUndo);
    });
  }

  function renderPagination(data) {
    const container = document.getElementById('recentlyDeletedPagination');
    if (!container) return;
    if (!data.next && !data.previous) {
      container.style.display = 'none';
      return;
    }
    container.style.display = 'flex';
    container.innerHTML = `
      <div style="display: flex; gap: 8px; justify-content: flex-end; align-items: center; width: 100%; padding: 1rem 0;">
        <button id="prevPageBtn" class="btn btn-sm btn-secondary" ${!data.previous ? 'disabled' : ''}>Oldingi</button>
        <span style="font-size: 0.875rem; color: rgba(255,255,255,0.7);">Jami: ${data.count || 0} ta</span>
        <button id="nextPageBtn" class="btn btn-sm btn-secondary" ${!data.next ? 'disabled' : ''}>Keyingi</button>
      </div>
    `;
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    if (prevBtn && data.previous) {
      prevBtn.addEventListener('click', () => fetchDeletedItems(data.previous));
    }
    if (nextBtn && data.next) {
      nextBtn.addEventListener('click', () => fetchDeletedItems(data.next));
    }
  }

  async function onUndo(e) {
    const btn = e.currentTarget;
    const itemType = btn.getAttribute('data-type');
    const itemId = btn.getAttribute('data-id');
    if (!confirm('Siz ushbu yozuvni tiklamoqchimisiz? (24 soat ichida mumkin)')) return;
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
        btn.closest('tr').remove();
        alert('Muvaffaqiyatli tiklandi (Restored)');
      } else {
        alert(json.message || 'Undo bajarilmadi');
      }
    } catch (err) {
      console.error(err);
      alert('Undo so\'rovida xatolik yuz berdi');
    }
  }

  document.addEventListener('DOMContentLoaded', () => fetchDeletedItems());
})();
