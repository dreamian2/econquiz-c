// ─────────────────────────────────────────
// Service Worker — 오늘의 경제 퀴즈 PWA
// 역할: 앱 파일을 캐시해서 오프라인에서도 동작하게 함
// ─────────────────────────────────────────

const CACHE_NAME = 'economy-quiz-v1';

// 오프라인에서도 쓸 수 있도록 저장할 파일 목록
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  'https://fonts.googleapis.com/css2?family=Gmarket+Sans:wght@300;500;700&family=Noto+Sans+KR:wght@400;700;900&display=swap'
];

// ── 설치: 앱 처음 열릴 때 파일들을 캐시에 저장 ──
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('📦 캐시 저장 중...');
      // 폰트는 실패해도 설치 계속 진행
      return cache.addAll(ASSETS).catch(() => {
        return cache.addAll(['./','./index.html','./manifest.json']);
      });
    })
  );
  self.skipWaiting();
});

// ── 활성화: 오래된 캐시 삭제 ──
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => {
            console.log('🗑️ 오래된 캐시 삭제:', key);
            return caches.delete(key);
          })
      )
    )
  );
  self.clients.claim();
});

// ── 요청 처리: 캐시 우선 → 없으면 네트워크 ──
self.addEventListener('fetch', event => {
  // quiz_*.json 파일은 항상 최신으로 (네트워크 우선)
  if (event.request.url.includes('quiz_')) {
    event.respondWith(
      fetch(event.request)
        .then(res => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
          return res;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // 나머지는 캐시 우선 (오프라인 지원)
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(res => {
        const copy = res.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
        return res;
      });
    })
  );
});
