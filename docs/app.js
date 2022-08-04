var versaoMobile = screen.width <= 478;
var paginaAtual = 'resumo';
var menuAtual = 'Início';

if('serviceWorker' in navigator) {
	navigator.serviceWorker.register('serviceWorker.js', { scope: '/Covid-19-em-Sao-Paulo/' })
		.then(
			function(registration) {
				var serviceWorker;
				
				if(registration.installing)
					serviceWorker = registration.installing;
				else if(registration.waiting)
					serviceWorker = registration.waiting;
				else if(registration.active)
					serviceWorker = registration.active;
				
				if(serviceWorker) {
					console.log('Status inicial do serviceWorker: ' + serviceWorker.state);
					
					serviceWorker.addEventListener('statechange', function(e) {
						console.log('Status do serviceWorker: ' + e.target.state);
						
						if(e.target.state === 'redundant')
							atualizaPagina();
					});
				}
			}
		)
		.catch(function(err) {
			console.log('Erro: não foi possível registrar o serviceWorker.', err);
		})
}
else {
	console.log('Não há suporte para serviceWorkers no momento.');
}

function atualizaPagina() {
  var d = document.getElementById('atualizacao');
  d.className = 'visivel';

  setTimeout(function() {d.className = d.className.replace('visivel', ''); location.reload();}, 3000);
}

function defineVisualizacao() {
	versaoMobile = screen.width <= 478;
	
	if(screen.width < 768) { //celulares, celulares em modo paisagem e tablets
		document.getElementById('menu-mobile').style.display = 'block';
		document.getElementById('menu-wrapper').style.display = 'none';				
		document.getElementById('aviso-mobile').style.display = 'list-item';
		document.getElementById('aviso-legendas').style.display = 'none';
	}
	else {
		document.getElementById('menu-mobile').style.display = 'none';
		document.getElementById('menu-wrapper').style.display = 'block';
		document.getElementById('aviso-mobile').style.display = 'none';
		document.getElementById('aviso-legendas').style.display = 'list-item';
	}
};

window.addEventListener('load', defineVisualizacao);
window.addEventListener('resize', defineVisualizacao);

function mostraMenu(novoTexto) {
	menuAtual = novoTexto;
	
	var menu = document.getElementById('opcoes');
	
	if(menu.style.display === 'block')
		menu.style.display = 'none';
	else
		menu.style.display = 'block';
	
	document.getElementById('label').innerHTML = menuAtual;
}

function escondeMenu() {
	document.getElementById('opcoes').style.display = 'none';
	document.getElementById('label').innerHTML = 'Início';
}

function criaTitulo(titulo) {		
	var h2 = document.createElement('h2');
	h2.innerText = titulo;
	
	var divTitulo = document.createElement('div');
	divTitulo.className = 'title';
	divTitulo.appendChild(h2);
	
	var divConteudo = document.getElementById('conteudo');
	divConteudo.insertAdjacentElement('beforeEnd', divTitulo);
}

function criaLink(descricao, linkDesktop) {	
	var a = document.createElement('a');
	a.innerText = descricao;
	a.href = linkDesktop;
	a.target = 'about:blank';
	
	var h2 = document.createElement('h2');
	h2.appendChild(a);
	
	var divSubTitulo = document.createElement('div');
	divSubTitulo.className = 'subtitle';
	divSubTitulo.appendChild(h2);
	
	var divConteudo = document.getElementById('conteudo');
	divConteudo.insertAdjacentElement('beforeEnd', divSubTitulo);
}

function criaIFrame(linkDesktop, linkMobile, versaoMobile) {	
	var iframe = document.createElement('iframe');
	iframe.src = versaoMobile ? linkMobile : linkDesktop;
	iframe.style.display = 'block';
	iframe.style.border = 'none';
	iframe.style.width = 1200;
	iframe.onload = function(iframe, versaoMobile) {
		var altura = iframe.currentTarget.contentDocument.body.scrollHeight;
		if(altura < 256) altura = 500;
		if(altura > 800) altura = 650;
		iframe.srcElement.height = altura;
		iframe.srcElement.style.height = altura;
	}

	var divConteudo = document.getElementById('conteudo');
	divConteudo.insertAdjacentElement('beforeEnd', iframe);
}
			
function montaPagina(pagina) {	
	//limpa página
	document.getElementById('conteudo').innerHTML = '';
	
	paginaAtual = pagina;
	
	switch(paginaAtual) {
		case 'resumo':
			criaTitulo('Resumo diário');
			
			criaLink('Ampliar resumo diário', 'graficos/resumo.html');
			criaIFrame('graficos/resumo.html', 'graficos/resumo-mobile.html', versaoMobile);
			
			criaTitulo('Semana Epidemiológica');
			
			criaLink('Ampliar resumo semanal', 'graficos/resumo-semanal.html');
			criaIFrame('graficos/resumo-semanal.html', 'graficos/resumo-semanal-mobile.html', versaoMobile);
			
			criaTitulo('Campanha de vacinação');
			
			criaLink('Ampliar resumo da campanha de vacinação', 'graficos/resumo-vacinacao.html');
			criaIFrame('graficos/resumo-vacinacao.html', 'graficos/resumo-vacinacao-mobile.html', versaoMobile);

			break;
			
		case 'evolucao':
			criaTitulo('Evolução da pandemia');
			
			criaLink('Ampliar gráfico da evolução da pandemia no estado', 'graficos/evolucao-estado.html');
			criaIFrame('graficos/evolucao-estado.html', 'graficos/evolucao-estado-mobile.html', versaoMobile);
			
			criaLink('Ampliar gráfico da evolução da pandemia na cidade', 'graficos/evolucao-cidade.html');
			criaIFrame('graficos/evolucao-cidade.html', 'graficos/evolucao-cidade-mobile.html', versaoMobile);
			
			criaTitulo('Casos no Estado');
			
			criaLink('Ampliar gráfico de casos no estado', 'graficos/casos-estado.html');
			criaIFrame('graficos/casos-estado.html', 'graficos/casos-estado-mobile.html', versaoMobile);
			
			criaTitulo('Casos na Cidade');
			
			criaLink('Ampliar gráfico de casos na cidade', 'graficos/casos-cidade.html');
			criaIFrame('graficos/casos-cidade.html', 'graficos/casos-cidade-mobile.html', versaoMobile);
			
			criaTitulo('Doenças preexistentes nos casos');
			
			criaLink('Ampliar gráfico de doenças preexistentes nos casos', 'graficos/doencas-casos.html');
			criaIFrame('graficos/doencas-casos.html', 'graficos/doencas-casos-mobile.html', versaoMobile);
			
			criaTitulo('Doenças preexistentes nos óbitos');
			
			criaLink('Ampliar gráfico de doenças preexistentes nos óbitos', 'graficos/doencas-obitos.html');
			criaIFrame('graficos/doencas-obitos.html', 'graficos/doencas-obitos-mobile.html', versaoMobile);
			
			criaTitulo('Raça/cor nos casos e óbitos');
			
			criaLink('Ampliar gráfico de raça/cor nos casos e óbitos', 'graficos/raca-cor.html');
			criaIFrame('graficos/raca-cor.html', 'graficos/raca-cor-mobile.html', versaoMobile);
			
			break;
		
		case 'isolamento':
			criaTitulo('Adesão ao Isolamento Social');
			
			criaLink('Ampliar gráfico do isolamento social', 'graficos/isolamento.html');
			criaIFrame('graficos/isolamento.html', 'graficos/isolamento-mobile.html', versaoMobile);
			
			criaLink('Ampliar tabela do isolamento social', 'graficos/tabela-isolamento.html');
			criaIFrame('graficos/tabela-isolamento.html', 'graficos/tabela-isolamento-mobile.html', versaoMobile);
			
			break;
			
		case 'leitos':
			criaTitulo('Ocupação de leitos no Estado');
			
			criaLink('Ampliar gráfico de ocupação de leitos no estado', 'graficos/leitos-estaduais.html');
			criaIFrame('graficos/leitos-estaduais.html', 'graficos/leitos-estaduais-mobile.html', versaoMobile);
			
			criaTitulo('Departamentos Regionais de Saúde');
			
			criaLink('Ampliar gráfico de leitos no DRS', 'graficos/drs.html');
			criaIFrame('graficos/drs.html', 'graficos/drs-mobile.html', versaoMobile);
			
			criaTitulo('Ocupação de leitos públicos na Cidade');
			
			criaLink('Ampliar gráfico da situação dos hospitais municipais', 'graficos/leitos-municipais.html');
			criaIFrame('graficos/leitos-municipais.html', 'graficos/leitos-municipais-mobile.html', versaoMobile);
			
			criaTitulo('Ocupação de leitos privados contratados pela Prefeitura');
			
			criaLink('Ampliar gráfico da situação dos leitos privados', 'graficos/leitos-municipais-privados.html');
			criaIFrame('graficos/leitos-municipais-privados.html', 'graficos/leitos-municipais-privados-mobile.html', versaoMobile);
			
			criaTitulo('Ocupação geral de leitos públicos e privados na Cidade');
			
			criaLink('Ampliar gráfico da situação dos leitos em geral', 'graficos/leitos-municipais-total.html');
			criaIFrame('graficos/leitos-municipais-total.html', 'graficos/leitos-municipais-total-mobile.html', versaoMobile);
			
			criaTitulo('Situação dos Hospitais Municipais de Campanha');
			
			criaLink('Ampliar gráfico do HMCamp do Pacaembu', 'graficos/pacaembu.html');
			criaIFrame('graficos/pacaembu.html', 'graficos/pacaembu-mobile.html', versaoMobile);
			
			criaLink('Ampliar gráfico do HMCamp do Anhembi', 'graficos/anhembi.html');
			criaIFrame('graficos/anhembi.html', 'graficos/anhembi-mobile.html', versaoMobile);
			
			break;
			
		case 'vacinacao':
			criaTitulo('Evolução da campanha de vacinação contra a Covid-19');
			
			criaLink('Ampliar gráfico da vacinação contra Covid-19 no estado', 'graficos/vacinacao-estado.html');
			criaIFrame('graficos/vacinacao-estado.html', 'graficos/vacinacao-estado-mobile.html', versaoMobile);
			
			criaLink('Ampliar gráfico da vacinação contra Covid-19 na cidade', 'graficos/vacinacao-cidade.html');
			criaIFrame('graficos/vacinacao-cidade.html', 'graficos/vacinacao-cidade-mobile.html', versaoMobile);
			
			criaLink('Ampliar gráfico da população vacinada contra Covid-19', 'graficos/populacao-vacinada.html');
			criaIFrame('graficos/populacao-vacinada.html', 'graficos/populacao-vacinada-mobile.html', versaoMobile);
			
			criaLink('Ampliar gráfico das doses de vacinas aplicadas', 'graficos/vacinas-tipo.html');
			criaIFrame('graficos/vacinas-tipo.html', 'graficos/vacinas-tipo-mobile.html', versaoMobile);
			
			criaLink('Ampliar gráfico das vacinas disponíveis x aplicadas', 'graficos/vacinas-aplicadas.html');
			criaIFrame('graficos/vacinas-aplicadas.html', 'graficos/vacinas-aplicadas-mobile.html', versaoMobile);
			
			criaLink('Ampliar gráfico dos imunizantes distribuídos', 'graficos/imunizantes.html');
			criaIFrame('graficos/imunizantes.html', 'graficos/imunizantes-mobile.html', versaoMobile);
			
			var descricao = '';
			
			if(versaoMobile)
				descricao = 'Ver a tabela completa da vacinação nos municípios';
			else
				descricao = 'Ampliar tabela da vacinação nos municípios';
			
			criaLink(descricao, 'graficos/tabela-vacinacao.html');
			criaIFrame('graficos/tabela-vacinacao.html', 'graficos/tabela-vacinacao-mobile.html', versaoMobile);
			
			break;
			
		default:
			alert('Erro: a opção "' + graf + '" não existe.');
	}
}

montaPagina(paginaAtual);
