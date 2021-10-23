const VERSAO = '01'
const CACHE_NAME = 'Covid19-SP-23/10/2021-' + VERSAO;

const CACHE_URLS = [
	'index.html',
	'manifest.json',
	'css/style.css',
	'serviceWorker.js',
	'app.js',
	'graficos/plotly.min.js',
	'graficos/anhembi-mobile.html',
	'graficos/anhembi.html',
	'graficos/casos-cidade-mobile.html',
	'graficos/casos-cidade.html',
	'graficos/casos-estado-mobile.html',
	'graficos/casos-estado.html',
	'graficos/isolamento-mobile.html',
	'graficos/isolamento.html',
	'graficos/leitos-municipais-mobile.html',
	'graficos/leitos-municipais.html',
	'graficos/leitos-estaduais-mobile.html',
	'graficos/leitos-estaduais.html',
	'graficos/pacaembu-mobile.html',
	'graficos/pacaembu.html',
	'graficos/resumo-mobile.html',
	'graficos/resumo.html',
	'graficos/resumo-vacinacao-mobile.html',
	'graficos/resumo-vacinacao.html',
	'graficos/tabela-isolamento-mobile.html',
	'graficos/tabela-isolamento.html',
	'graficos/evolucao-estado.html',
	'graficos/evolucao-estado-mobile.html',
	'graficos/evolucao-cidade.html',
	'graficos/evolucao-cidade-mobile.html',
	'graficos/resumo-semanal-mobile.html',
	'graficos/resumo-semanal.html',
	'graficos/leitos-municipais-privados-mobile.html',
	'graficos/leitos-municipais-privados.html',
	'graficos/leitos-municipais-total-mobile.html',
	'graficos/leitos-municipais-total.html',
	'graficos/drs-mobile.html',
	'graficos/drs.html',
	'graficos/doencas-casos-mobile.html',
	'graficos/doencas-casos.html',
	'graficos/doencas-obitos-mobile.html',
	'graficos/doencas-obitos.html',
	'graficos/vacinacao-estado-mobile.html',
	'graficos/vacinacao-estado.html',
	'graficos/vacinacao-cidade-mobile.html',
	'graficos/vacinacao-cidade.html',
	'graficos/populacao-vacinada-mobile.html',
	'graficos/populacao-vacinada.html',
	'graficos/vacinas-aplicadas-mobile.html',
	'graficos/vacinas-aplicadas.html',
	'graficos/vacinas-tipo-mobile.html',
	'graficos/vacinas-tipo.html',
	'graficos/tabela_vacinacao.html',
	'graficos/tabela-vacinacao-mobile.html',
	'images/bg01.png',	
	'icons/android-chrome-192x192.png',
	'icons/android-chrome-512x512.png',
	'icons/apple-touch-icon.png',
	'icons/favicon-16x16.png',
	'icons/favicon-32x32.png',
	'icons/favicon.ico'
];

// The install handler takes care of precaching the resources we always need.
self.addEventListener('install', event => {	
	console.log('O serviceWorker está salvando os arquivos no cache...');
	
	event.waitUntil(
		caches.open(CACHE_NAME)
			.then(cache => cache.addAll(CACHE_URLS))
			.then(self.skipWaiting())
			.catch(function(err) {
				console.log("O serviceWorker não salvou os arquivos em cache.", err);
			})
	);
});

// The activate handler takes care of cleaning up old caches.
self.addEventListener('activate', event => {
	event.waitUntil(
		caches.keys().then(function(cacheNames) {
			return Promise.all(cacheNames.map(function(thisCacheName) {
				if (thisCacheName !== CACHE_NAME) {
					console.log('O serviceWorker está excluindo o cache', thisCacheName);
					return caches.delete(thisCacheName);
				}
			}));
		})
		.then(() => self.clients.claim())
		.catch(function(err) {
			console.log("O serviceWorker não foi ativado.", err);
		})
	);
});

// The fetch handler serves responses for same-origin resources from
// a cache. If no response is found, it populates the cache with the
// response from the network before returning it to the page.
self.addEventListener('fetch', event => {
	if(event.request.url.startsWith(self.location.origin)) {
		event.respondWith(
			caches.match(event.request).then(cachedResponse => {
				if(cachedResponse) {
					console.log('O serviceWorker buscou dados em cache.');
					return cachedResponse;
				}

				console.log('O serviceWorker buscou dados do servidor.');

				return caches.open(CACHE_NAME).then(cache => {
					return fetch(event.request).then(response => {
						return cache.put(event.request, response.clone()).then(() => {
							return response;
						});
					});
				});
			})
			.catch(function(err) {
				console.log("O serviceWorker não conseguiu buscar dados.", err);
			})
		);
	}
});
