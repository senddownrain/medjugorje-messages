import { clientsClaim } from 'workbox-core';
import { precacheAndRoute, createHandlerBoundToURL } from 'workbox-precaching';
import { registerRoute, NavigationRoute } from 'workbox-routing';
import { CacheFirst } from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';

clientsClaim();
// New shell is installed completely before activation. Never delete old data on install.
precacheAndRoute(self.__WB_MANIFEST);
registerRoute(new NavigationRoute(createHandlerBoundToURL('index.html')));
const base = new URL('./', self.location.href).pathname;
// Keep the complete last successful snapshot pointer for each explicitly loaded
// language, so a data update in RU does not strand a previously saved LV offline.
registerRoute(({ url }) => url.origin === self.location.origin &&
  new RegExp('^' + base + 'data/latest-for-(ru|be|uk|hr|en|sk|lv)\\.json$').test(url.pathname),
  async ({ request }) => await (await caches.open('message-manifest-schema-1')).match(request) || Response.error());
registerRoute(({ url }) => url.origin === self.location.origin && url.pathname === base + 'data/latest.json',
  async ({ request }) => {
    const cache = await caches.open('message-manifest-schema-1');
    try {
      const response = await fetch(request, { cache:'no-store' });
      const manifest = response.ok && await response.clone().json();
      if (!manifest || manifest.schema_version !== 1 || !/^[a-f0-9]{24}$/.test(manifest.data_version)) throw new Error('Incompatible manifest');
      // Commit the pointer only after this device's selected latest record is safely cached
      // by the client. The previous pointer remains a usable offline fallback meanwhile.
      return response;
    } catch (error) {
      const cached = await cache.match(request);
      if (cached) return cached;
      throw error;
    }
  });

registerRoute(({ url }) => url.origin === self.location.origin &&
  new RegExp('^' + base + 'data/[a-f0-9]{24}/[a-z-]+\\.json$').test(url.pathname),
  new CacheFirst({ cacheName:'message-immutable-data-v1', plugins:[
    { async cacheWillUpdate({ request, response }) {
      if (!response.ok || !response.headers.get('content-type')?.includes('json')) return null;
      try {
        const value = await response.clone().json();
        const [version, file] = new URL(request.url).pathname.slice((base + 'data/').length).split('/');
        if (file.startsWith('latest-')) {
          if (value.schema_version !== 1 || value.data_version !== version || file !== `latest-${value.language}.json`) return null;
        } else if (file === 'metadata.json') {
          if (value.schema_version !== 1 || !Array.isArray(value.messages)) return null;
        } else if (file !== `${value.language}.json` || !Array.isArray(value.messages)) return null;
        return response;
      } catch { return null; }
    } }, new ExpirationPlugin({ maxEntries:32, purgeOnQuotaError:false })
  ] }));
registerRoute(({ url }) => url.origin === self.location.origin && url.pathname.startsWith(base + 'assets/'),
  new CacheFirst({ cacheName:'message-demand-code-v1', plugins:[
    new CacheableResponsePlugin({ statuses:[200] }), new ExpirationPlugin({ maxEntries:40, purgeOnQuotaError:false })
  ] }));

self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
  if (event.data?.type !== 'COMMIT_MANIFEST') return;
  event.waitUntil((async () => {
    const { manifest, language, latest } = event.data;
    if (manifest?.schema_version !== 1 || !/^[a-f0-9]{24}$/.test(manifest.data_version) ||
        !['ru','be','uk','hr','en','sk','lv'].includes(language)) return;
    const path = manifest.latest?.[language]?.file;
    if (path !== `${manifest.data_version}/latest-${language}.json`) return;
    const url = base + 'data/' + path;
    const dataCache = await caches.open('message-immutable-data-v1');
    // First visit can fetch before SW control; seed just this latest record after readiness.
    const response = await dataCache.match(url) || new Response(JSON.stringify(latest), { headers:{ 'Content-Type':'application/json' } });
    if (!response.ok) return;
    const value = await response.clone().json();
    if (value.data_version !== manifest.data_version || value.language !== language) return;
    await dataCache.put(url, response);
    const cache = await caches.open('message-manifest-schema-1');
    const pointer = new Response(JSON.stringify(manifest), { headers:{ 'Content-Type':'application/json' } });
    await cache.put(base + `data/latest-for-${language}.json`, pointer.clone());
    await cache.put(base + 'data/latest.json', pointer);
    event.ports[0]?.postMessage('committed');
  })());
});
