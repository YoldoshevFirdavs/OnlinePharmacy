const SearchEngineFactory = {
    _engines: {
        google: { name: 'google', param: 'q' },
        bing: { name: 'bing', param: 'q' },
        yahoo: { name: 'yahoo', param: 'p' },
    },
    getSearchEngineAnalyzer(name) {
        const key = (name || 'google').toLowerCase();
        // Ensure a fallback to google if the key doesn't exist
        return this._engines[key] || this._engines['google'];
    },
};

function detectSearchEngine() {
    const ref = document.referrer || '';
    if (ref.includes('bing.com')) return 'bing';
    if (ref.includes('yahoo.com')) return 'yahoo';
    return 'google';
}

// Ensure this script runs only once
if (typeof window.searchAnalyzerInitialized === 'undefined') {
    window.searchAnalyzerInitialized = true;

    const engineName = detectSearchEngine();
    const engine = SearchEngineFactory.getSearchEngineAnalyzer(engineName) || SearchEngineFactory.getSearchEngineAnalyzer('google');

    if (!engine || !engine.param) {
        console.warn('Search engine not initialized, defaulting to Google.');
        return;
    }

    const params = new URLSearchParams(window.location.search);
    const query = params.get(engine.param) || params.get('q') || '';
    if (query) {
        document.dispatchEvent(new CustomEvent('searchAnalyzed', {
            detail: {
                engine: engine.name,
                query
            }
        }));
    }
}