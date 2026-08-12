// static/js/api.js
// Global apiPost funksiyasi, Content-Type tekshiruvi bilan
window.apiPost = async function(url, payload, method = 'POST', opts = {}) {
    const fetchOpts = {
        method,
        headers: {
            'Accept': 'application/json', // Serverdan JSON kutayotganimizni bildiramiz
            'Content-Type': 'application/json',
            ...(opts.headers || {})
        },
        credentials: opts.credentials || 'same-origin'
    };

    if (payload !== null) {
        fetchOpts.body = JSON.stringify(payload);
    }

    try {
        const res = await fetch(url, fetchOpts);
        const contentType = res.headers.get('content-type') || '';
        const text = await res.text(); // Javobni avval text sifatida olamiz

        // Agar server JSON qaytarmasa (masalan, HTML xato sahifasi), xatolikni tutamiz
        if (!contentType.includes('application/json')) {
            console.error(`apiPost: Serverdan kutilmagan javob (Content-Type: ${contentType}). URL: ${url}`, text);
            // HTML javobni ham qaytaramiz, shunda chaqiruvchi funksiya uni ko'rsatishi mumkin
            return { status: res.status, data: null, html: text };
        }

        let data;
        try {
            data = text ? JSON.parse(text) : {};
        } catch (e) {
            console.error(`apiPost: Serverdan noto'g'ri JSON javob. URL: ${url}`, text);
            throw new Error(`Serverdan noto'g'ri JSON javob: ${res.status} ${res.statusText}.`);
        }

        if (!res.ok) {
            const errorMessage = data.detail || data.message || `Xato: ${res.status} ${res.statusText}`;
            console.error(`apiPost: API xatosi. URL: ${url}`, data);
            throw new Error(errorMessage);
        }

        return { status: res.status, data: data }; // status va data ni birga qaytaramiz
    } catch (error) {
        if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
            console.error('apiPost: Tarmoq xatosi. Serverga ulanib bo‘lmadi.', error);
            throw new Error('Tarmoq xatosi. Iltimos internet aloqangizni tekshiring.');
        }
        console.error('apiPost: Kutilmagan xato.', error);
        throw error; // Boshqa xatolarni qayta tashlaymiz
    }
};
