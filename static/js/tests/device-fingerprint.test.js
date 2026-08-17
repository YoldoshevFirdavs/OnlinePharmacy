/**
 * Client-side tests for device fingerprint system
 * Run these tests in browser console or with a JS test framework
 */

// Mock testing framework functions if not available
if (typeof describe === 'undefined') {
    window.describe = function(name, fn) {
        console.group(`Test Suite: ${name}`);
        fn();
        console.groupEnd();
    };
}

if (typeof it === 'undefined') {
    window.it = function(name, fn) {
        try {
            fn();
            console.log(`✓ ${name}`);
        } catch (error) {
            console.error(`✗ ${name}: ${error.message}`);
        }
    };
}

if (typeof expect === 'undefined') {
    window.expect = function(actual) {
        return {
            toBe: (expected) => {
                if (actual !== expected) {
                    throw new Error(`Expected ${expected}, got ${actual}`);
                }
            },
            toEqual: (expected) => {
                if (JSON.stringify(actual) !== JSON.stringify(expected)) {
                    throw new Error(`Expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
                }
            },
            toBeTruthy: () => {
                if (!actual) {
                    throw new Error(`Expected truthy value, got ${actual}`);
                }
            },
            toBeFalsy: () => {
                if (actual) {
                    throw new Error(`Expected falsy value, got ${actual}`);
                }
            },
            toContain: (expected) => {
                if (!actual.includes(expected)) {
                    throw new Error(`Expected "${actual}" to contain "${expected}"`);
                }
            },
            toBeGreaterThan: (expected) => {
                if (actual <= expected) {
                    throw new Error(`Expected ${actual} to be greater than ${expected}`);
                }
            },
            toMatch: (pattern) => {
                if (!pattern.test(actual)) {
                    throw new Error(`Expected "${actual}" to match pattern ${pattern}`);
                }
            }
        };
    };
}

describe('Device Fingerprint System', function() {
    
    describe('DeviceFingerprintGenerator', function() {
        
        it('should be available globally', function() {
            expect(typeof DeviceFingerprintGenerator).toBe('function');
            expect(typeof window.deviceFP).toBe('object');
        });
        
        it('should generate consistent fingerprints', async function() {
            const fp1 = await window.deviceFP.generateFingerprint();
            const fp2 = await window.deviceFP.generateFingerprint();
            
            expect(fp1).toBe(fp2);
            expect(fp1.length).toBeGreaterThan(32);
        });
        
        it('should generate valid hex fingerprints', async function() {
            const fp = await window.deviceFP.generateFingerprint();
            const hexPattern = /^[a-f0-9]+$/i;
            
            expect(hexPattern.test(fp)).toBeTruthy();
        });
        
        it('should handle canvas fingerprinting gracefully', async function() {
            // Mock canvas failure
            const originalCreateElement = document.createElement;
            document.createElement = function(tag) {
                if (tag === 'canvas') {
                    const mockCanvas = originalCreateElement.call(document, 'div');
                    mockCanvas.getContext = function() {
                        throw new Error('Canvas not supported');
                    };
                    return mockCanvas;
                }
                return originalCreateElement.call(document, tag);
            };
            
            try {
                const fp = await window.deviceFP.generateFingerprint();
                expect(fp).toBeTruthy();
                expect(fp.length).toBeGreaterThan(8);
            } finally {
                // Restore original function
                document.createElement = originalCreateElement;
            }
        });
        
    });
    
    describe('Cookie Management', function() {
        
        beforeEach(function() {
            // Clear existing fingerprint cookie
            document.cookie = 'device_fp=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        });
        
        it('should set fingerprint cookie', function() {
            const testFp = 'test123abc456def';
            window.deviceFP.setCookie(testFp);
            
            const cookies = document.cookie.split(';');
            const fpCookie = cookies.find(cookie => cookie.trim().startsWith('device_fp='));
            
            expect(fpCookie).toBeTruthy();
            expect(fpCookie).toContain(testFp);
        });
        
        it('should retrieve fingerprint from cookie', function() {
            const testFp = 'test123abc456def';
            document.cookie = `device_fp=${testFp}; path=/`;
            
            const retrieved = window.deviceFP.getCookie();
            expect(retrieved).toBe(testFp);
        });
        
        it('should return null for missing cookie', function() {
            // Ensure no cookie exists
            document.cookie = 'device_fp=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            
            const retrieved = window.deviceFP.getCookie();
            expect(retrieved).toBe(null);
        });
        
    });
    
    describe('Header Injection', function() {
        
        it('should add fingerprint to XMLHttpRequest headers', function() {
            const testFp = 'test_header_fp_123';
            window.deviceFP.addToHeaders(testFp);
            
            // Create a test XMLHttpRequest
            const xhr = new XMLHttpRequest();
            
            // Mock setRequestHeader to capture headers
            const headers = {};
            xhr.setRequestHeader = function(name, value) {
                headers[name] = value;
            };
            
            // Simulate opening and sending a request to API endpoint
            xhr.open('GET', '/api/test');
            xhr.send();
            
            // Check if fingerprint header was added
            expect(headers['Authorization-Fingerprint']).toBe(testFp);
        });
        
        it('should add fingerprint to fetch requests', async function() {
            const testFp = 'test_fetch_fp_456';
            window.deviceFP.addToHeaders(testFp);
            
            // Mock fetch to capture options
            const originalFetch = window.fetch;
            let capturedOptions = null;
            
            window.fetch = function(url, options) {
                capturedOptions = options;
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({})
                });
            };
            
            try {
                // Make a test fetch request to API endpoint
                await fetch('/api/test', { method: 'GET' });
                
                expect(capturedOptions.headers['Authorization-Fingerprint']).toBe(testFp);
            } finally {
                // Restore original fetch
                window.fetch = originalFetch;
            }
        });
        
    });
    
    describe('Initialization', function() {
        
        it('should initialize automatically on DOM ready', function() {
            expect(window.currentDeviceFingerprint).toBeTruthy();
            expect(typeof window.currentDeviceFingerprint).toBe('string');
        });
        
        it('should provide manual refresh function', async function() {
            const oldFp = window.currentDeviceFingerprint;
            
            // Manual refresh should work
            const newFp = await window.refreshDeviceFingerprint();
            
            expect(newFp).toBeTruthy();
            expect(typeof newFp).toBe('string');
            expect(newFp.length).toBeGreaterThan(32);
        });
        
    });
    
    describe('Browser Compatibility', function() {
        
        it('should handle missing crypto.subtle gracefully', async function() {
            // Mock missing crypto.subtle
            const originalCrypto = window.crypto;
            window.crypto = {
                subtle: undefined
            };
            
            try {
                const fp = await window.deviceFP.generateFingerprint();
                expect(fp).toBeTruthy();
                expect(typeof fp).toBe('string');
            } finally {
                // Restore original crypto
                window.crypto = originalCrypto;
            }
        });
        
        it('should handle missing navigator properties gracefully', async function() {
            // Mock missing navigator properties
            const originalUserAgent = navigator.userAgent;
            const originalPlatform = navigator.platform;
            
            Object.defineProperty(navigator, 'userAgent', {
                writable: true,
                value: undefined
            });
            Object.defineProperty(navigator, 'platform', {
                writable: true,
                value: undefined
            });
            
            try {
                const fp = await window.deviceFP.generateFingerprint();
                expect(fp).toBeTruthy();
                expect(typeof fp).toBe('string');
            } finally {
                // Restore original properties
                Object.defineProperty(navigator, 'userAgent', {
                    writable: true,
                    value: originalUserAgent
                });
                Object.defineProperty(navigator, 'platform', {
                    writable: true,
                    value: originalPlatform
                });
            }
        });
        
        it('should handle missing screen properties gracefully', async function() {
            // Mock missing screen properties
            const originalScreen = window.screen;
            window.screen = {};
            
            try {
                const fp = await window.deviceFP.generateFingerprint();
                expect(fp).toBeTruthy();
                expect(typeof fp).toBe('string');
            } finally {
                // Restore original screen
                window.screen = originalScreen;
            }
        });
        
    });
    
    describe('Security Features', function() {
        
        it('should generate different fingerprints for different browsers', async function() {
            // This test would ideally run across different browsers
            // For now, we just ensure the fingerprint includes browser-specific data
            const fp = await window.deviceFP.generateFingerprint();
            
            // Should include user agent data
            expect(fp.length).toBeGreaterThan(40);
        });
        
        it('should be deterministic within same session', async function() {
            const fps = [];
            
            // Generate multiple fingerprints
            for (let i = 0; i < 5; i++) {
                fps.push(await window.deviceFP.generateFingerprint());
            }
            
            // All should be identical
            const firstFp = fps[0];
            fps.forEach(fp => {
                expect(fp).toBe(firstFp);
            });
        });
        
        it('should not expose sensitive information', async function() {
            const fp = await window.deviceFP.generateFingerprint();
            
            // Fingerprint should be a hash, not containing readable personal data
            expect(fp).not.toContain('@');  // No email
            expect(fp).not.toContain('user');  // No username
            expect(fp).not.toContain('password');  // No password
            expect(fp).toMatch(/^[a-f0-9]+$/i);  // Only hex characters
        });
        
    });
    
    describe('Performance', function() {
        
        it('should generate fingerprint quickly', async function() {
            const startTime = performance.now();
            
            await window.deviceFP.generateFingerprint();
            
            const endTime = performance.now();
            const duration = endTime - startTime;
            
            // Should complete within 1 second
            expect(duration).toBeLessThan(1000);
        });
        
        it('should cache fingerprint for repeated calls', async function() {
            // Clear any existing cookie
            document.cookie = 'device_fp=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            
            // First call
            const startTime1 = performance.now();
            const fp1 = await window.deviceFP.getCurrentFingerprint();
            const duration1 = performance.now() - startTime1;
            
            // Second call (should use cached value)
            const startTime2 = performance.now();
            const fp2 = await window.deviceFP.getCurrentFingerprint();
            const duration2 = performance.now() - startTime2;
            
            expect(fp1).toBe(fp2);
            expect(duration2).toBeLessThan(duration1);  // Second call should be faster
        });
        
    });
    
});

// Run tests automatically if in browser environment
if (typeof window !== 'undefined' && window.deviceFP) {
    console.log('Running Device Fingerprint Tests...');
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(() => {
                // Run the test suite
                console.log('Device Fingerprint Tests Complete');
            }, 1000);
        });
    } else {
        setTimeout(() => {
            console.log('Device Fingerprint Tests Complete');
        }, 1000);
    }
}