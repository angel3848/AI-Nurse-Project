const CACHE_NAME = 'ai-nurse-v1';
const APP_SHELL = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
];

// Install: cache the app shell
self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function(cache) {
            return cache.addAll(APP_SHELL);
        })
    );
    self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(keys) {
            return Promise.all(
                keys.filter(function(key) {
                    return key !== CACHE_NAME;
                }).map(function(key) {
                    return caches.delete(key);
                })
            );
        })
    );
    self.clients.claim();
});

// Fetch: serve from cache first, fall back to network
self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request).then(function(cachedResponse) {
            if (cachedResponse) {
                return cachedResponse;
            }
            return fetch(event.request).then(function(response) {
                // Only cache successful same-origin responses
                if (!response || response.status !== 200 || response.type !== 'basic') {
                    return response;
                }
                var responseToCache = response.clone();
                caches.open(CACHE_NAME).then(function(cache) {
                    cache.put(event.request, responseToCache);
                });
                return response;
            });
        })
    );
});

// Push: show a notification when a push event is received
self.addEventListener('push', function(event) {
    var data = {
        title: 'AI Nurse',
        body: 'You have a new notification.',
        icon: '/static/icon-192.png',
    };
    if (event.data) {
        try {
            var payload = event.data.json();
            data.title = payload.title || data.title;
            data.body = payload.body || data.body;
            data.icon = payload.icon || data.icon;
        } catch (e) {
            data.body = event.data.text() || data.body;
        }
    }
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: data.icon,
        })
    );
});

// Notification click: open the app
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        self.clients.matchAll({ type: 'window' }).then(function(clients) {
            for (var i = 0; i < clients.length; i++) {
                if (clients[i].url === '/' && 'focus' in clients[i]) {
                    return clients[i].focus();
                }
            }
            if (self.clients.openWindow) {
                return self.clients.openWindow('/');
            }
        })
    );
});
