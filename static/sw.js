self.addEventListener('push', function (event) {
    const payload = event.data ? event.data.json() : {
        title: 'BESTTIVE Notification',
        body: 'You have a new admin notification.',
        tag: 'besttive-admin',
        url: '/admin/notifications'
    };

    console.log('Service worker push event received:', payload);

    const title = payload.title || 'BESTTIVE Notification';
    const options = {
        body: payload.body || '',
        tag: payload.tag || 'besttive-admin',
        icon: '/static/images/logo.png',
        badge: '/static/images/logo.png',
        data: {
            url: payload.url || '/admin/notifications'
        },
        requireInteraction: true,
        silent: false
    };

    console.log('Showing browser notification:', title, options);
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function (event) {
    event.notification.close();

    const url = event.notification.data && event.notification.data.url
        ? event.notification.data.url
        : '/admin/notifications';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (clientList) {
            for (const client of clientList) {
                if (client.url.includes('/admin') && 'focus' in client) {
                    return client.focus();
                }
            }
            return clients.openWindow(url);
        })
    );
});
