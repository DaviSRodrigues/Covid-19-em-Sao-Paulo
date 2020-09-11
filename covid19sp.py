# -*- coding: utf-8 -*-
"""
Covid-19 em São Paulo

Gera gráficos para acompanhamento da pandemia de Covid-19
na cidade e no estado de São Paulo.

@author: https://github.com/DaviSRodrigues
"""

from datetime import datetime, timedelta
import locale
import math
import traceback

from bs4 import BeautifulSoup
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
import requests
import tabula

def main():
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

    print('Carregando dados...')
    dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total = carrega_dados_cidade()
    dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais = carrega_dados_estado()

    print('\nLimpando e enriquecendo dos dados...')
    dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total, dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais = pre_processamento(dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total, dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais)
    efeito_cidade, efeito_estado = gera_dados_efeito_isolamento(dados_cidade, dados_estado, isolamento)
    efeito_cidade, efeito_estado = gera_dados_semana(efeito_cidade, leitos_municipais_total, efeito_estado, leitos_estaduais, isolamento, internacoes)

    print('\nGerando gráficos e tabelas...')
    gera_graficos(dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total, dados_estado, isolamento, leitos_estaduais, efeito_cidade, efeito_estado, internacoes, doencas, dados_raciais)

    print('\nAtualizando serviceWorker.js...')    
    atualiza_service_worker(dados_cidade)
    
    print('\nFim')

def carrega_dados_cidade():
    dados_cidade = pd.read_csv('dados/dados_cidade_sp.csv', sep = ',')
    hospitais_campanha = pd.read_csv('dados/hospitais_campanha_sp.csv', sep = ',')
    leitos_municipais = pd.read_csv('dados/leitos_municipais.csv', sep = ',')
    leitos_municipais_privados = pd.read_csv('dados/leitos_municipais_privados.csv', sep = ',')
    leitos_municipais_total = pd.read_csv('dados/leitos_municipais_total.csv', sep = ',')
    
    return extrair_dados_prefeitura(dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total)

def extrair_dados_prefeitura(dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total):
    def formata_numero(valor):
        valor = str(valor)
        valor = valor.split('(')[0]
        valor = valor.split('*')[0]
        
        if valor == '-':
            return math.nan
        
        if '%' in valor:
            valor = valor.replace('%', '')
            
        if math.isnan(float(valor)):
            return math.nan
        
        if '.' in valor:
            return int(valor.replace('.', ''))
        
        return int(valor)
    
    try:
        data = datetime.now()
        data_str = f'{data.day} de {data:%B} de {data:%Y}'
        
        if data.day == 1:
            data_str = data_str.replace('1 de ', '1º de ')
            
        #página de Boletins da Prefeitura de São Paulo
        URL = ('https://www.prefeitura.sp.gov.br/cidade/secretarias/saude/vigilancia_em_saude/doencas_e_agravos/coronavirus/index.php?p=295572')
        boletim_disponivel = False
        
        for i in range(2):
            pagina = requests.get(URL)

            soup = BeautifulSoup(pagina.text, 'html.parser')
            
            for link in soup.find_all('a'):
                if(data_str in link.text):
                    URL = link['href']
                    boletim_disponivel = True
                    break
                    
        if boletim_disponivel:
            data_str = data.strftime('%d/%m/%Y')
            data_cidade = datetime.strptime(dados_cidade.tail(1).data.iat[0], '%d/%m/%Y')
            
            if(data.date() > data_cidade.date()):
                dados_novos = True
                print('\tExtraindo dados novos de ' + data_str + '...')
            else:
                dados_novos = False
                print('\tAtualizando dados existentes de ' + data_str + '...')
                        
            print('\tURL do boletim municipal: ' + URL)
        else:
            raise Exception(f'O boletim de {data_str} ainda não está disponível.')

        #com a URL do pdf correto, começa a extração de dados
        tabelas = tabula.read_pdf(URL, pages = 2, guess = False, lattice = True, pandas_options = {'dtype': 'str'})
        resumo = tabelas[0]
        obitos = tabelas[1]

        tabelas = tabula.read_pdf(URL, pages = 4, guess = True, lattice = True, pandas_options = {'dtype': 'str'})
        hm_camp = tabelas[0]
        info_leitos = tabelas[1]
        
        #atualiza dados municipais        
        if(dados_novos):
            novos_dados = {'data': [data_str],
                           'suspeitos': [formata_numero(resumo.tail(1).iat[0,1])],
                           'confirmados': [formata_numero(resumo.tail(1).iat[0,2])],
                           'óbitos': [math.nan],
                           'óbitos_suspeitos': [math.nan]}
            
            dados_cidade = dados_cidade.append(
                pd.DataFrame(novos_dados,
                             columns = ['data', 'suspeitos', 'confirmados', 'óbitos', 'óbitos_suspeitos']),
                ignore_index = True)
        else:
            dados_cidade.loc[dados_cidade.data == data_str, 'suspeitos'] = formata_numero(resumo.tail(1).iat[0,1])
            dados_cidade.loc[dados_cidade.data == data_str, 'confirmados'] = formata_numero(resumo.tail(1).iat[0,2])
        
        #atualiza hospitais de campanha
        # if(dados_novos):
        #     novos_dados = {'data': [data_str],
        #                    'hospital': ['Anhembi'],
        #                    'leitos': [887],
        #                    'comum': [813],
        #                    'uti': [74],
        #                    'ocupação_comum': [formata_numero(hm_camp.iat[1, 1])],
        #                    'ocupação_uti': [formata_numero(hm_camp.iat[2, 1])],
        #                    'altas': [formata_numero(hm_camp.iat[3, 1])],
        #                    'óbitos': [formata_numero(hm_camp.iat[4, 1])],
        #                    'transferidos': [formata_numero(hm_camp.iat[5, 1])],
        #                    'chegando': [formata_numero(hm_camp.iat[6, 1])]}
            
        #     hospitais_campanha = hospitais_campanha.append(
        #         pd.DataFrame(novos_dados,
        #                      columns = ['data', 'hospital', 'leitos', 'comum', 'uti', 'ocupação_comum',
        #                                 'ocupação_uti', 'altas', 'óbitos', 'transferidos', 'chegando']),
        #         ignore_index = True)
        # else:
        #     hospitais_campanha.loc[((hospitais_campanha.data == data_str) & (hospitais_campanha.hospital == 'Anhembi')), 'ocupação_comum'] = formata_numero(hm_camp.iat[1, 1])
        #     hospitais_campanha.loc[((hospitais_campanha.data == data_str) & (hospitais_campanha.hospital == 'Anhembi')), 'ocupação_uti'] = formata_numero(hm_camp.iat[2, 1])
        #     hospitais_campanha.loc[((hospitais_campanha.data == data_str) & (hospitais_campanha.hospital == 'Anhembi')), 'altas'] = formata_numero(hm_camp.iat[3, 1])
        #     hospitais_campanha.loc[((hospitais_campanha.data == data_str) & (hospitais_campanha.hospital == 'Anhembi')), 'óbitos'] = formata_numero(hm_camp.iat[4, 1])
        #     hospitais_campanha.loc[((hospitais_campanha.data == data_str) & (hospitais_campanha.hospital == 'Anhembi')), 'transferidos'] = formata_numero(hm_camp.iat[5, 1])
        #     hospitais_campanha.loc[((hospitais_campanha.data == data_str) & (hospitais_campanha.hospital == 'Anhembi')), 'chegando'] = formata_numero(hm_camp.iat[6, 1])
                
        #atualiza leitos municipais
        if(dados_novos):
            novos_dados = {'data': [data_str],
                           'respiratorio_publico': [formata_numero(info_leitos.iat[0, 1])],
                           'suspeitos_publico': [formata_numero(info_leitos.iat[1, 1])],
                           'internados_publico': [formata_numero(info_leitos.iat[2, 1])],
                           'uti_covid_publico': [formata_numero(info_leitos.iat[3, 1])],
                           'internados_uti_publico': [formata_numero(info_leitos.iat[4, 1])],
                           'ventilacao_publico': [formata_numero(info_leitos.iat[5, 1])],
                           'ocupacao_uti_covid_publico': [formata_numero(info_leitos.iat[6, 1])]}
            
            leitos_municipais = leitos_municipais.append(
                pd.DataFrame(novos_dados,
                             columns = ['data', 'respiratorio_publico', 'suspeitos_publico',
                                        'internados_publico', 'uti_covid_publico', 'internados_uti_publico',
                                        'ventilacao_publico', 'ocupacao_uti_covid_publico']),
                ignore_index = True)
            
            novos_dados = {'data': [data_str],
                           'respiratorio_privado': [formata_numero(info_leitos.iat[0, 2])],
                           'suspeitos_privado': [formata_numero(info_leitos.iat[1, 2])],
                           'internados_privado': [formata_numero(info_leitos.iat[2, 2])],
                           'uti_covid_privado': [formata_numero(info_leitos.iat[3, 2])],
                           'internados_uti_privado': [formata_numero(info_leitos.iat[4, 2])],
                           'ventilacao_privado': [formata_numero(info_leitos.iat[5, 2])],
                           'ocupacao_uti_covid_privado': [formata_numero(info_leitos.iat[6, 2])]}
            
            leitos_municipais_privados = leitos_municipais_privados.append(
                pd.DataFrame(novos_dados,
                             columns = ['data', 'respiratorio_privado', 'suspeitos_privado',
                                        'internados_privado', 'uti_covid_privado', 'internados_uti_privado',
                                        'ventilacao_privado', 'ocupacao_uti_covid_privado']),
                ignore_index = True)
            
            novos_dados = {'data': [data_str],
                           'respiratorio_total': [formata_numero(info_leitos.iat[0, 3])],
                           'suspeitos_total': [formata_numero(info_leitos.iat[1, 3])],
                           'internados_total': [formata_numero(info_leitos.iat[2, 3])],
                           'uti_covid_total': [formata_numero(info_leitos.iat[3, 3])],
                           'internados_uti_total': [formata_numero(info_leitos.iat[4, 3])],
                           'ventilacao_total': [formata_numero(info_leitos.iat[5, 3])],
                           'ocupacao_uti_covid_total': [formata_numero(info_leitos.iat[6, 3])]}
            
            leitos_municipais_total = leitos_municipais_total.append(
                pd.DataFrame(novos_dados,
                             columns = ['data', 'respiratorio_total', 'suspeitos_total',
                                        'internados_total', 'uti_covid_total', 'internados_uti_total',
                                        'ventilacao_total', 'ocupacao_uti_covid_total']),
                ignore_index = True)
        else:
            leitos_municipais.loc[leitos_municipais.data == data_str, 'respiratorio_publico'] = formata_numero(info_leitos.iat[0, 1])
            leitos_municipais.loc[leitos_municipais.data == data_str, 'suspeitos_publico'] = formata_numero(info_leitos.iat[1, 1])
            leitos_municipais.loc[leitos_municipais.data == data_str, 'internados_publico'] = formata_numero(info_leitos.iat[2, 1])
            leitos_municipais.loc[leitos_municipais.data == data_str, 'uti_covid_publico'] = formata_numero(info_leitos.iat[3, 1])
            leitos_municipais.loc[leitos_municipais.data == data_str, 'internados_uti_publico'] = formata_numero(info_leitos.iat[4, 1])
            leitos_municipais.loc[leitos_municipais.data == data_str, 'ventilacao_publico'] = formata_numero(info_leitos.iat[5, 1])
            leitos_municipais.loc[leitos_municipais.data == data_str, 'ocupacao_uti_covid_publico'] = formata_numero(info_leitos.iat[6, 1])
            
            leitos_municipais_privados.loc[leitos_municipais_privados.data == data_str, 'respiratorio_privado'] = formata_numero(info_leitos.iat[0, 2])
            leitos_municipais_privados.loc[leitos_municipais_privados.data == data_str, 'suspeitos_privado'] = formata_numero(info_leitos.iat[1, 2])
            leitos_municipais_privados.loc[leitos_municipais_privados.data == data_str, 'internados_privado'] = formata_numero(info_leitos.iat[2, 2])
            leitos_municipais_privados.loc[leitos_municipais_privados.data == data_str, 'uti_covid_privado'] = formata_numero(info_leitos.iat[3, 2])
            leitos_municipais_privados.loc[leitos_municipais_privados.data == data_str, 'internados_uti_privado'] = formata_numero(info_leitos.iat[4, 2])
            leitos_municipais_privados.loc[leitos_municipais_privados.data == data_str, 'ventilacao_privado'] = formata_numero(info_leitos.iat[5, 2])
            leitos_municipais_privados.loc[leitos_municipais_privados.data == data_str, 'ocupacao_uti_covid_privado'] = formata_numero(info_leitos.iat[6, 2])
            
            leitos_municipais_total.loc[leitos_municipais_total.data == data_str, 'respiratorio_total'] = formata_numero(info_leitos.iat[0, 3])
            leitos_municipais_total.loc[leitos_municipais_total.data == data_str, 'suspeitos_total'] = formata_numero(info_leitos.iat[1, 3])
            leitos_municipais_total.loc[leitos_municipais_total.data == data_str, 'internados_total'] = formata_numero(info_leitos.iat[2, 3])
            leitos_municipais_total.loc[leitos_municipais_total.data == data_str, 'uti_covid_total'] = formata_numero(info_leitos.iat[3, 3])
            leitos_municipais_total.loc[leitos_municipais_total.data == data_str, 'internados_uti_total'] = formata_numero(info_leitos.iat[4, 3])
            leitos_municipais_total.loc[leitos_municipais_total.data == data_str, 'ventilacao_total'] = formata_numero(info_leitos.iat[5, 3])
            leitos_municipais_total.loc[leitos_municipais_total.data == data_str, 'ocupacao_uti_covid_total'] = formata_numero(info_leitos.iat[6, 3])
        
        def atualizaObitos(series):
            nonlocal data
            
            if len(series[0].split('-')) > 1:
                sep = '-'
            elif len(series[0].split('/')) > 1:
                sep = '/'
            elif len(series[0].split(' ')) > 1:
                sep = ' '
            
            if series[0].split(sep)[1].isnumeric():
                mes = '%m'
            else:
                mes = '%b'
                
            if len(series[0].split(sep)) >= 3:
                if len(series[0].split(sep)[2]) == 2:
                    ano = '%y'
                else:
                    ano = '%Y'
            else:
                ano = '%Y'            
                series[0] = series[0] + sep + data.strftime('%Y')
            
            try:
                dt_obito = datetime.strptime(series[0], '%d' + sep + mes + sep + ano)
            except ValueError:
                raise ValueError('Não foi possível identificar o formato das datas de óbitos do boletim municipal.')
            
            dt_obito = dt_obito.strftime('%d/%m/%Y')
            
            dados_cidade.loc[dados_cidade.data == dt_obito, 'óbitos'] = formata_numero(series[1])
            dados_cidade.loc[dados_cidade.data == dt_obito, 'óbitos_suspeitos'] = formata_numero(series[5])
        
        #remove a primeira linha vazia e atualiza os dados, sem alterar o dataframe original
        obitos.drop([0,1]).apply(lambda linha: atualizaObitos(linha), axis = 1)
        
        #após a extração dos dados e a montagem de dataframes, a atualização dos arquivos
        dados_cidade.to_csv('dados/dados_cidade_sp.csv', sep = ',', index  = False)
        hospitais_campanha.to_csv('dados/hospitais_campanha_sp.csv', sep = ',', index  = False)
        leitos_municipais.to_csv('dados/leitos_municipais.csv', sep = ',', index  = False)
        leitos_municipais_privados.to_csv('dados/leitos_municipais_privados.csv', sep = ',', index  = False)
        leitos_municipais_total.to_csv('dados/leitos_municipais_total.csv', sep = ',', index  = False)
    except Exception as e:
        traceback.print_exception(type(e), e, e.__traceback__)
    
    return dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total

def carrega_dados_estado():
    try:
        print('\tAtualizando dados estaduais...')
        URL = ('https://raw.githubusercontent.com/seade-R/dados-covid-sp/master/data/sp.csv')
        dados_estado = pd.read_csv(URL, sep = ';')
        dados_estado.to_csv('dados/dados_estado_sp.csv', sep = ';')
    except Exception as e:
        traceback.print_exception(type(e), e, e.__traceback__)
        print('\tErro ao buscar dados_estado_sp.csv do GitHub: lendo arquivo local.\n')
        dados_estado = pd.read_csv('dados/dados_estado_sp.csv', sep = ';', decimal = ',', encoding = 'latin-1', index_col = 0)
        
    try:
        print('\tAtualizando dados de isolamento social...')
        URL = ('https://public.tableau.com/views/IsolamentoSocial/DADOS.csv?:showVizHome=no')
        isolamento = pd.read_csv(URL, sep = ',')
        isolamento.to_csv('dados/isolamento_social.csv', sep = ',')
    except Exception as e:
        print(f'\tErro ao buscar isolamento_social.csv do Tableau: lendo arquivo local.\n\t{e}')
        isolamento = pd.read_csv('dados/isolamento_social.csv', sep = ',', index_col = 0)
    
    try:
        print('\tAtualizando dados de internações...')
        URL = ('https://raw.githubusercontent.com/seade-R/dados-covid-sp/master/data/plano_sp_leitos_internacoes.csv')
        internacoes = pd.read_csv(URL, sep = ';', decimal = ',', thousands = '.')
        internacoes.to_csv('dados/internacoes.csv', sep = ';', decimal = ',')
    except Exception as e:
        try:    
            print(f'\tErro ao buscar internacoes.csv do GitHub: lendo arquivo da Seade.\n\t{e}')
            URL = ('http://www.seade.gov.br/wp-content/uploads/2020/08/Leitos-e-Internacoes.csv')
            internacoes = pd.read_csv(URL, sep = ';', encoding = 'latin-1', decimal = ',', thousands = '.', engine = 'python', skipfooter = 2)
        except Exception as e:
            print(f'\tErro ao buscar internacoes.csv da Seade: lendo arquivo local.\n\t{e}')
            internacoes = pd.read_csv('dados/internacoes.csv', sep = ';', decimal = ',', thousands = '.', index_col = 0)
    
    try:
        print('\tAtualizando dados de doenças preexistentes...')
        URL = ('https://raw.githubusercontent.com/seade-R/dados-covid-sp/master/data/casos_obitos_doencas_preexistentes.csv.zip')
        doencas = pd.read_csv(URL, sep = ';')
        opcoes_zip = dict(method = 'zip', archive_name = 'doencas_preexistentes.csv')
        doencas.to_csv('dados/doencas_preexistentes.zip', sep = ';', compression = opcoes_zip)
    except Exception as e:                        
        try:
            print(f'\tErro ao buscar doencas_preexistentes.csv do GitHub: lendo arquivo local.\n\t{e}')
            doencas = pd.read_csv('dados/doencas_preexistentes.zip', sep = ';', index_col = 0)
        except Exception as e:
            print(f'\tErro ao buscar doencas_preexistentes.csv localmente: lendo arquivo da Seade.\n\t{e}')
            mes = datetime.now().strftime('%m')
            URL = 'http://www.seade.gov.br/wp-content/uploads/2020/' + mes + '/casos_obitos_doencas_preexistentes.csv'
            doencas = pd.read_csv(URL, sep = ';', encoding = 'latin-1')
            
    try:
        print('\tAtualizando dados de casos/óbitos por raça e cor...')
        URL = ('https://raw.githubusercontent.com/seade-R/dados-covid-sp/master/data/casos_obitos_raca_cor.csv.zip')
        dados_raciais = pd.read_csv(URL, sep = ';')
        opcoes_zip = dict(method = 'zip', archive_name = 'dados_raciais.csv')
        dados_raciais.to_csv('dados/dados_raciais.zip', sep = ';', compression = opcoes_zip)
    except Exception as e:
        print(f'\tErro ao buscar dados_raciais.csv do GitHub: lendo arquivo local.\n\t{e}')
        dados_raciais = pd.read_csv('dados/dados_raciais.zip', sep = ';', index_col = 0)
        
    leitos_estaduais = pd.read_csv('dados/leitos_estaduais.csv', index_col = 0)
    
    return dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais

def pre_processamento(dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total, dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais):
    print('\tDados municipais...')
    dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total = pre_processamento_cidade(dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total)
    print('\tDados estaduais...')
    dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais = pre_processamento_estado(dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais)
    
    return dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total, dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais

def pre_processamento_cidade(dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total):
    dados_cidade['data'] = pd.to_datetime(dados_cidade.data, format = '%d/%m/%Y')
    dados_cidade['dia'] = dados_cidade.data.apply(lambda d: d.strftime('%d %b'))
    
    hospitais_campanha['data'] = pd.to_datetime(hospitais_campanha.data, format = '%d/%m/%Y')
    hospitais_campanha['dia'] = hospitais_campanha.data.apply(lambda d: d.strftime('%d %b'))
        
    leitos_municipais['data'] = pd.to_datetime(leitos_municipais.data, format = '%d/%m/%Y')
    leitos_municipais['dia'] = leitos_municipais.data.apply(lambda d: d.strftime('%d %b'))
    
    leitos_municipais_privados['data'] = pd.to_datetime(leitos_municipais_privados.data, format = '%d/%m/%Y')
    leitos_municipais_privados['dia'] = leitos_municipais_privados.data.apply(lambda d: d.strftime('%d %b'))
    
    leitos_municipais_total['data'] = pd.to_datetime(leitos_municipais_total.data, format = '%d/%m/%Y')
    leitos_municipais_total['dia'] = leitos_municipais_total.data.apply(lambda d: d.strftime('%d %b'))
    
    def calcula_letalidade(series):
        #calcula a taxa de letalidade até a data atual
        series['letalidade'] = round((series['óbitos'] / series['confirmados']) * 100, 2)
        return series
    
    def calcula_dia(series):
        #localiza a linha atual passada como parâmetro e obtém a linha anterior
        indice = dados_cidade.index[dados_cidade.dia == series['dia']].item() - 1
        
        if(indice >= 0):
            casos_conf_anterior = dados_cidade.loc[indice, 'confirmados']
            casos_susp_anterior = dados_cidade.loc[indice, 'suspeitos']
            obitos_conf_anterior = dados_cidade.loc[indice, 'óbitos']
            obitos_susp_anterior = dados_cidade.loc[indice, 'óbitos_suspeitos']
            
            series['casos_dia'] = series['confirmados'] - casos_conf_anterior
            series['óbitos_dia'] = series['óbitos'] - obitos_conf_anterior
            series['casos_suspeitos_dia'] = series['suspeitos'] - casos_susp_anterior
            series['óbitos_suspeitos_dia'] = series['óbitos_suspeitos'] - obitos_susp_anterior
        
        return series
    
    dados_cidade = dados_cidade.apply(lambda linha: calcula_letalidade(linha), axis = 1)
    dados_cidade = dados_cidade.apply(lambda linha: calcula_dia(linha), axis = 1)
    
    return dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total

def pre_processamento_estado(dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais):
    dados_estado.columns = ['data', 'total_casos', 'total_obitos']
    dados_estado['data'] = pd.to_datetime(dados_estado.data)
    dados_estado['dia'] = dados_estado.data.apply(lambda d: d.strftime('%d %b'))
    
    def formata_municipio(m):
        return m.title() \
                .replace(' Da ', ' da ') \
                .replace(' De ', ' de ') \
                .replace(' Do ', ' do ') \
                .replace(' Das ', ' das ') \
                .replace(' Dos ', ' dos ')
                
    isolamento.columns = ['codigo_ibge', 'data', 'município', 'UF', 'isolamento']
    #deixando apenas a primeira letra de cada palavra como maiúscula
    isolamento['município'] = isolamento.município.apply(lambda m: formata_municipio(m))
    isolamento['isolamento'] = pd.to_numeric(isolamento.isolamento.str.replace('%', ''))
    isolamento['data'] = isolamento.data.apply(lambda d: datetime.strptime(d.split(', ')[1] + '/2020', '%d/%m/%Y'))
    isolamento['dia'] = isolamento.data.apply(lambda d: d.strftime('%d %b'))
    isolamento.sort_values(by = ['data', 'isolamento'], inplace = True)
    
    leitos_estaduais['data'] = pd.to_datetime(leitos_estaduais.data, format = '%d/%m/%Y')
    
    internacoes.columns = ['data', 'drs', 'pacientes_uti_mm7d', 'total_covid_uti_mm7d', 'ocupacao_leitos', 'pop', 'leitos_pc', 'internacoes_7d', 'internacoes_7d_l', 'internacoes_7v7']
    internacoes['data'] = pd.to_datetime(internacoes.data)
    internacoes['dia'] = internacoes.data.apply(lambda d: d.strftime('%d %b'))
    
    if internacoes.data.max() > leitos_estaduais.data.max():
        novos_dados = {'data': internacoes.data.max(),
                       'sp_uti': None,
                       'sp_enfermaria': None,
                       'rmsp_uti': None,
                       'rmsp_enfermaria': None}
        
        leitos_estaduais = leitos_estaduais.append(novos_dados, ignore_index = True)
    
    def atualizaOcupacaoUTI(series):
        ocupacao = internacoes.loc[(internacoes.drs == 'Estado de São Paulo') & (internacoes.data == series['data']), 'ocupacao_leitos']
        series['sp_uti'] = ocupacao.item() if any(ocupacao) else series['sp_uti']
        
        filtro_drs = ((internacoes.drs.str.contains('SP')) | (internacoes.drs == 'Município de São Paulo'))
        leitos = internacoes.loc[(filtro_drs) & (internacoes.data == series['data']), 'total_covid_uti_mm7d'].sum()
        
        if leitos > 0:
            pacientes = internacoes.loc[(filtro_drs) & (internacoes.data == series['data']), 'pacientes_uti_mm7d'].sum()
            ocupacao = pacientes / leitos
            series['rmsp_uti'] = round(ocupacao * 100, 2)
        
        return series
    
    leitos_estaduais = leitos_estaduais.apply(lambda linha: atualizaOcupacaoUTI(linha), axis = 1)
    
    leitos_estaduais['dia'] = leitos_estaduais.data.apply(lambda d: d.strftime('%d %b'))
    leitos_estaduais['data'] = leitos_estaduais.data.apply(lambda d: d.strftime('%d/%m/%Y'))
    colunas = ['data', 'sp_uti', 'sp_enfermaria', 'rmsp_uti', 'rmsp_enfermaria']
    leitos_estaduais[colunas].to_csv('dados/leitos_estaduais.csv', sep = ',')
    leitos_estaduais['data'] = pd.to_datetime(leitos_estaduais.data, format = '%d/%m/%Y')
    
    doencas.columns = ['municipio', 'codigo_ibge', 'idade', 'sexo', 'covid19', 'data_inicio_sintomas', 'obito', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica', 'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera', 'sindrome_de_down']
    
    doencas = doencas.groupby(['obito', 'covid19', 'idade', 'sexo', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica', 'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera', 'sindrome_de_down']) \
                     .agg({'asma': 'count', 'cardiopatia': 'count', 'diabetes': 'count', 'doenca_hematologica': 'count', 'doenca_hepatica' : 'count', 'doenca_neurologica' : 'count', 'doenca_renal' : 'count', 'imunodepressao' : 'count', 'obesidade' : 'count', 'outros' : 'count', 'pneumopatia' : 'count', 'puerpera' : 'count', 'sindrome_de_down' : 'count'})
    
    def calcula_letalidade(series):
        #localiza a linha atual passada como parâmetro e obtém a o índice da linha anterior
        indice = dados_estado.index[dados_estado.data == series['data']].item() - 1
        
        if indice >= 0:
            series['casos_dia'] = series['total_casos'] - dados_estado.loc[indice, 'total_casos']
            series['obitos_dia'] = series['total_obitos'] - dados_estado.loc[indice, 'total_obitos']
        else:
            series['casos_dia'] = series['total_casos']
            series['obitos_dia'] = series['total_obitos']
            
        #calcula a taxa de letalidade até a data atual
        if series['total_casos'] > 0:
            series['letalidade'] = round((series['total_obitos'] / series['total_casos']) * 100, 2)
        
        return series
    
    dados_estado = dados_estado.apply(lambda linha: calcula_letalidade(linha), axis = 1)
    
    dados_raciais = dados_raciais[['obito', 'raca_cor']]
    dados_raciais = dados_raciais.fillna('IGNORADO')
    dados_raciais.loc[dados_raciais.raca_cor == 'NONE', 'raca_cor'] = 'IGNORADO'
    dados_raciais['raca_cor'] = dados_raciais.raca_cor.str.title()
    dados_raciais = dados_raciais.groupby(['obito', 'raca_cor']).agg(contagem = ('obito', 'count'))
    
    return dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais

def _converte_semana(data):
    return data.strftime('%Y-W%U')
    
def _formata_semana_extenso(data):
    #http://portalsinan.saude.gov.br/calendario-epidemiologico-2020
    return datetime.strptime(data + '-0', '%Y-W%U-%w').strftime('%d/%b') + ' a ' + \
           datetime.strptime(data + '-6', '%Y-W%U-%w').strftime('%d/%b')

def gera_dados_efeito_isolamento(dados_cidade, dados_estado, isolamento):
    print('\tCalculando efeito do isolamento social...')
    #criar dataframe relação: comparar média de isolamento social de duas
    #semanas atrás com a quantidade de casos e de óbitos da semana atual    
    isolamento['data_futuro'] = isolamento.data.apply(lambda d: d + timedelta(weeks = 2))
    
    filtro = isolamento.município == 'Estado de São Paulo'
    colunas = ['data_futuro', 'isolamento']

    esquerda = isolamento.loc[filtro, colunas] \
                         .groupby(['data_futuro']).mean().reset_index()

    esquerda.columns = ['data', 'isolamento']

    estado = dados_estado[['data', 'obitos_dia', 'casos_dia']] \
                    .groupby(['data']).sum().reset_index()
        
    estado.columns = ['data', 'obitos_semana', 'casos_semana']

    estado = esquerda.merge(estado, on = ['data'], how = 'outer', suffixes = ('_isolamento', '_estado'))

    estado['data'] = estado.data.apply(lambda d: _converte_semana(d))

    estado = estado.groupby('data') \
                   .agg({'isolamento': 'mean', 'obitos_semana': sum, 'casos_semana': sum}) \
                   .reset_index()

    estado['data'] = estado.data.apply(lambda d: _formata_semana_extenso(d))
    
    estado['casos_semana'] = estado.casos_semana.apply(lambda c: math.nan if c == 0 else c)
    estado['obitos_semana'] = estado.obitos_semana.apply(lambda c: math.nan if c == 0 else c)
    
    efeito_estado = estado

    #dados municipais
    filtro = isolamento.município == 'São Paulo'
    colunas = ['data_futuro', 'isolamento']

    esquerda = isolamento.loc[filtro, colunas] \
                         .groupby(['data_futuro']).mean().reset_index()

    esquerda.columns = ['data', 'isolamento']

    cidade = dados_cidade[['data', 'óbitos_dia', 'casos_dia']] \
                    .groupby(['data']).sum().reset_index()

    cidade.columns = ['data', 'obitos_semana', 'casos_semana']
    cidade['município'] = 'São Paulo'

    cidade = esquerda.merge(cidade, on = ['data'], how = 'outer', suffixes = ('_isolamento', '_cidade'))

    cidade['data'] = cidade.data.apply(lambda d: _converte_semana(d))
    
    cidade = cidade.groupby('data') \
                   .agg({'isolamento': 'mean', 'obitos_semana': sum, 'casos_semana': sum}) \
                   .reset_index()

    cidade['data'] = cidade.data.apply(lambda d: _formata_semana_extenso(d))
    
    cidade['casos_semana'] = cidade.casos_semana.apply(lambda c: math.nan if c == 0 else c)
    cidade['obitos_semana'] = cidade.obitos_semana.apply(lambda c: math.nan if c == 0 else c)
    
    efeito_cidade = cidade
    
    return efeito_cidade, efeito_estado

def gera_dados_semana(efeito_cidade, leitos_municipais, efeito_estado, leitos_estaduais, isolamento, internacoes):
    print('\tCalculando dados semanais...')
    
    def calcula_variacao(dados, linha):
        indice = dados.index[dados.data == linha['data']].item() - 1
        
        if indice >= 0:
            casos_anterior = dados.loc[indice, 'casos_semana']
            obitos_anterior = dados.loc[indice, 'obitos_semana']
            uti_anterior = dados.loc[indice, 'uti']
            isolamento_anterior = dados.loc[indice, 'isolamento_atual']
            isolamento_2sem_anterior = dados.loc[indice, 'isolamento']
            
            if casos_anterior > 0:
                linha['variacao_casos'] = ((linha['casos_semana'] / casos_anterior) - 1) * 100
                
            if obitos_anterior > 0:
                linha['variacao_obitos'] = ((linha['obitos_semana'] / obitos_anterior) - 1) * 100
                
            if uti_anterior > 0:
                linha['variacao_uti'] = ((linha['uti'] / uti_anterior) - 1) * 100
                        
            if isolamento_anterior > 0:
                linha['variacao_isolamento'] = ((linha['isolamento_atual'] / isolamento_anterior) - 1) * 100
                
            if isolamento_2sem_anterior > 0:
                linha['variacao_isolamento_2sem'] = ((linha['isolamento'] / isolamento_2sem_anterior) - 1) * 100

        return linha
    
    #cálculo da média da taxa de ocupação de leitos de UTI na semana
    leitos = pd.DataFrame()
    leitos['data'] = leitos_municipais.data.apply(lambda d: _formata_semana_extenso(_converte_semana(d)))
    leitos['uti'] = leitos_municipais.ocupacao_uti_covid_total
    
    leitos = leitos.groupby('data').mean().reset_index()
    
    efeito_cidade = efeito_cidade.merge(leitos, on = 'data', how = 'outer', suffixes = ('_efeito', '_leitos'))
    
    filtro = isolamento.município == 'São Paulo'
    colunas = ['data', 'isolamento']
    
    isola_atual = isolamento.loc[filtro, colunas]
    isola_atual['data'] = isola_atual.data.apply(lambda d: _formata_semana_extenso(_converte_semana(d)))
    isola_atual = isola_atual.groupby('data').mean().reset_index()
    isola_atual.columns = ['data', 'isolamento_atual']
    
    efeito_cidade = efeito_cidade.merge(isola_atual, on = 'data', how = 'left', suffixes = ('_efeito', '_isola'))
    
    efeito_cidade = efeito_cidade.apply(lambda linha: calcula_variacao(efeito_cidade, linha), axis = 1)
    
    def obter_internacoes(local, linha):
        df = internacoes.loc[:, ['data', 'drs', 'internacoes_7d', 'internacoes_7v7']]
        df['data'] = df.data.apply(lambda d: _formata_semana_extenso(_converte_semana(d)))
        
        df = df[(df.data == linha.data) & (df.drs == local)]
        
        if df.empty:
            return linha
        
        linha['internacoes'] = df.tail(1).internacoes_7d.item()
        linha['variacao_internacoes'] = df.tail(1).internacoes_7v7.item()
        
        return linha
    
    efeito_cidade = efeito_cidade.apply(lambda linha: obter_internacoes('Município de São Paulo', linha), axis = 1)
    
    #dados estaduais
    leitos = pd.DataFrame()
    leitos['data'] = leitos_estaduais.data.apply(lambda d: _formata_semana_extenso(_converte_semana(d)))
    leitos['uti'] = leitos_estaduais.sp_uti
    
    leitos = leitos.groupby('data').mean().reset_index()
    
    efeito_estado = efeito_estado.merge(leitos, on = 'data', how = 'outer', suffixes = ('_efeito', '_leitos'))  
        
    filtro = isolamento.município == 'Estado de São Paulo'
    colunas = ['data', 'isolamento']
    
    isola_atual = isolamento.loc[filtro, colunas]
    isola_atual['data'] = isola_atual.data.apply(lambda d: _formata_semana_extenso(_converte_semana(d)))
    isola_atual = isola_atual.groupby('data').mean().reset_index()
    isola_atual.columns = ['data', 'isolamento_atual']
    
    efeito_estado = efeito_estado.merge(isola_atual, on = 'data', how = 'left', suffixes = ('_efeito', '_isola'))
    
    efeito_estado = efeito_estado.apply(lambda linha: calcula_variacao(efeito_estado, linha), axis = 1)
    
    efeito_estado = efeito_estado.apply(lambda linha: obter_internacoes('Estado de São Paulo', linha), axis = 1)
    
    return efeito_cidade, efeito_estado

def gera_graficos(dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total, dados_estado, isolamento, leitos_estaduais, efeito_cidade, efeito_estado, internacoes, doencas, dados_raciais):
    print('\tResumo diário...')
    gera_resumo_diario(dados_cidade, leitos_municipais_total, dados_estado, leitos_estaduais, isolamento, internacoes)
    print('\tResumo semanal...')
    gera_resumo_semanal(efeito_cidade, efeito_estado)
    print('\tCasos no estado...')
    gera_casos_estado(dados_estado)
    print('\tCasos na cidade...')
    gera_casos_cidade(dados_cidade)
    print('\tDoenças preexistentes nos casos estaduais...')
    gera_doencas_preexistentes_casos(doencas)
    print('\tDoenças preexistentes nos óbitos estaduais...')
    gera_doencas_preexistentes_obitos(doencas)
    print('\tCasos e óbitos estaduais por raça/cor...')
    gera_casos_obitos_por_raca_cor(dados_raciais)
    print('\tIsolamento social...')
    gera_isolamento_grafico(isolamento)
    print('\tTabela de isolamento social...')
    gera_isolamento_tabela(isolamento)
    print('\tEfeitos do isolamento social no estado...')
    gera_efeito_estado(efeito_estado)
    print('\tEfeitos do isolamento social na cidade...')
    gera_efeito_cidade(efeito_cidade)
    print('\tLeitos no estado...')
    gera_leitos_estaduais(leitos_estaduais)
    print('\tDepartamentos Regionais de Saúde...')
    gera_drs(internacoes)
    print('\tLeitos públicos na cidade...')
    gera_leitos_municipais(leitos_municipais)
    print('\tLeitos privados na cidade...')
    gera_leitos_municipais_privados(leitos_municipais_privados)
    print('\tLeitos em geral na cidade...')
    gera_leitos_municipais_total(leitos_municipais_total)
    print('\tHospitais de campanha...')
    gera_hospitais_campanha(hospitais_campanha)

def gera_resumo_diario(dados_cidade, leitos_municipais, dados_estado, leitos_estaduais, isolamento, internacoes):
    cabecalho = ['<b>Resumo diário</b>',
                 '<b>Estado de SP</b><br><i>' + dados_estado.tail(1).data.item().strftime('%d/%m/%Y') + '</i>', 
                 '<b>Cidade de SP</b><br><i>' + dados_cidade.tail(1).data.item().strftime('%d/%m/%Y') + '</i>']

    info = ['<b>Casos</b>', '<b>Casos no dia</b>', '<b>Óbitos</b>', '<b>Óbitos no dia</b>',
            '<b>Letalidade</b>', '<b>Leitos Covid-19</b>', '<b>Ocupação de UTIs</b>', '<b>Isolamento</b>']
    
    filtro = (isolamento.município == 'Estado de São Paulo') & (isolamento.data == isolamento.data.max())
    indice = isolamento.loc[filtro, 'isolamento'].iloc[0]
    
    estado = ['{:7,.0f}'.format(dados_estado.tail(1).total_casos.item()).replace(',', '.'), #Casos
              '{:7,.0f}'.format(dados_estado.tail(1).casos_dia.item()).replace(',', '.'), #Casos por dia
              '{:7,.0f}'.format(dados_estado.tail(1).total_obitos.item()).replace(',', '.'), #Óbitos
              '{:7,.0f}'.format(dados_estado.tail(1).obitos_dia.item()).replace(',', '.'), #Óbitos por dia
              '{:7.2f}%'.format(dados_estado.tail(1).letalidade.item()).replace('.', ','), #Letalidade
              '{:7,.0f}'.format(internacoes.loc[internacoes.drs == 'Estado de São Paulo', 'total_covid_uti_mm7d'].tail(1).item()).replace(',', '.'), #Leitos Covid-19
              '{:7.1f}%'.format(leitos_estaduais.tail(1).sp_uti.item()).replace('.', ','), #Ocupação de UTI 
              '{:7.0f}%'.format(indice)] #Isolamento social
    
    filtro = (isolamento.município == 'São Paulo') & (isolamento.data == isolamento.data.max())
    indice = isolamento.loc[filtro, 'isolamento'].iloc[0]
    
    cidade = ['{:7,.0f}'.format(dados_cidade.tail(1).confirmados.item()).replace(',', '.'), #Casos
              '{:7,.0f}'.format(dados_cidade.tail(1).casos_dia.item()).replace(',', '.'), #Casos por dia
              '{:7,.0f}'.format(dados_cidade.tail(2).head(1).óbitos.item()).replace(',', '.'), #Óbitos
              '{:7,.0f}'.format(dados_cidade.tail(2).head(1).óbitos_dia.item()).replace(',', '.'), #Óbitos por dia
              '{:7.2f}%'.format(dados_cidade.tail(2).head(1).letalidade.item()).replace('.', ','), #Letalidade
              '{:7,.0f}'.format(leitos_municipais.tail(1).uti_covid_total.item()).replace(',', '.'), #Leitos Covid-19
              '{:7.0f}%'.format(leitos_municipais.tail(1).ocupacao_uti_covid_total.item()), #Ocupação de UTI 
              '{:7.0f}%'.format(indice)] #Isolamento social
    
    fig = go.Figure(data = [go.Table(header = dict(values = cabecalho,
                                                   fill_color = '#00aabb',
                                                   font = dict(color = 'white'),
                                                   align = ['right', 'right', 'right'],
                                                   line = dict(width = 5)),
                                     cells = dict(values = [info, estado, cidade],
                                                  fill_color = 'lavender',
                                                  align = 'right',
                                                  line = dict(width = 5)),
                                     columnwidth = [1, 1, 1])])
    
    fig.update_layout(
        font = dict(size = 15, family = 'Roboto'),
        margin = dict(l = 1, r = 1, b = 1, t = 30, pad = 5),
        annotations = [dict(x = 0, y = 0, showarrow = False, font = dict(size = 13),
                            text = '<i><b>Fontes:</b> <a href = "https://www.seade.gov.br/coronavirus/">Governo do Estado ' + 
                                   'de São Paulo</a> e <a href = "https://www.prefeitura.sp.gov.br/cidade/secretarias/' +
                                   'saude/vigilancia_em_saude/doencas_e_agravos/coronavirus/index.php?p=295572">Prefeitura' +
                                   ' de São Paulo</a></i>')],
        height = 380
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/resumo.html', include_plotlyjs = 'directory', auto_open = False)
    
    fig.update_layout(
        font = dict(size = 13),
        margin = dict(l = 1, r = 1, b = 1, t = 30, pad = 5),
        annotations = [dict(x = 0, y = 0)],
        height = 370
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/resumo-mobile.html', include_plotlyjs = 'directory', auto_open = False)

def _formata_variacao(v):
    if math.isnan(v):
        return ''
    
    return '+{:02.1f}%'.format(v) if v >= 0 else '{:02.1f}%'.format(v)

def gera_resumo_semanal(efeito_cidade, efeito_estado):
    #%W: semana começa na segunda-feira
    hoje = datetime.now()
    hoje_formatado = int(f'{hoje:%W}') + 1
    
    #%U: semana começa no domingo
    hoje = datetime.now() - timedelta(days = 1)
    semana = _formata_semana_extenso(_converte_semana(hoje))
    num_semana = efeito_estado.index[efeito_estado.data == semana].item()
    
    cabecalho = [f'<b>{hoje_formatado}ª semana<br>epidemiológica</b>',
                 f'<b>Estado de SP</b><br>{semana}',
                 f'<b>Cidade de SP</b><br>{semana}']

    info = ['<b>Casos</b>', '<b>Variação</b>',
            '<b>Óbitos</b>', '<b>Variação</b>',
            '<b>Internações</b>', '<b>Variação</b>',
            '<b>Ocupação de UTIs</b>', '<b>Variação</b>',
            '<b>Isolamento</b>', '<b>Variação</b>']
    
    estado = ['{:7,.0f}'.format(efeito_estado.loc[num_semana, 'casos_semana']).replace(',', '.'), #Casos
              '<i>' + _formata_variacao(efeito_estado.loc[num_semana, 'variacao_casos']).replace('.', ',') + '</i>', #Variação casos
              '{:7,.0f}'.format(efeito_estado.loc[num_semana, 'obitos_semana']).replace(',', '.'), #óbitos
              '<i>' + _formata_variacao(efeito_estado.loc[num_semana, 'variacao_obitos']).replace('.', ',') + '</i>', #Variação óbitos
              '{:7,.0f}'.format(efeito_estado.loc[num_semana, 'internacoes']).replace(',', '.'), #Internações
              '<i>' + _formata_variacao(efeito_estado.loc[num_semana, 'variacao_internacoes']).replace('.', ',') + '</i>', #Variação de internações
              '{:7.1f}%'.format(efeito_estado.loc[num_semana, 'uti']).replace('.', ','), #Ocupação de UTIs
              '<i>' + _formata_variacao(efeito_estado.loc[num_semana, 'variacao_uti']).replace('.', ',') + '</i>', #Variação ocupação de UTIs
              '{:7.1f}%'.format(efeito_estado.loc[num_semana, 'isolamento_atual']).replace('.', ','), #Isolamento social
              '<i>' + _formata_variacao(efeito_estado.loc[num_semana, 'variacao_isolamento']).replace('.', ',') + '</i>'] #Variação isolamento
    
    num_semana = efeito_cidade.index[efeito_cidade.data == semana].item()
    
    cidade = ['{:7,.0f}'.format(efeito_cidade.loc[num_semana, 'casos_semana']).replace(',', '.'), #Casos
              '<i>' + _formata_variacao(efeito_cidade.loc[num_semana, 'variacao_casos']).replace('.', ',') + '</i>', #Variação casos
              '{:7,.0f}'.format(efeito_cidade.loc[num_semana, 'obitos_semana']).replace(',', '.'), #óbitos
              '<i>' + _formata_variacao(efeito_cidade.loc[num_semana, 'variacao_obitos']).replace('.', ',') + '</i>', #Variação óbitos
              '{:7,.0f}'.format(efeito_cidade.loc[num_semana, 'internacoes']).replace(',', '.'), #Internações
              '<i>' + _formata_variacao(efeito_cidade.loc[num_semana, 'variacao_internacoes']).replace('.', ',') + '</i>', #Variação de internações
              '{:7.1f}%'.format(efeito_cidade.loc[num_semana, 'uti']).replace('.', ','), #Ocupação de UTIs
              '<i>' + _formata_variacao(efeito_cidade.loc[num_semana, 'variacao_uti']).replace('.', ',') + '</i>', #Variação ocupação de UTIs
              '{:7.1f}%'.format(efeito_cidade.loc[num_semana, 'isolamento_atual']).replace('.', ','), #Isolamento social
              '<i>' + _formata_variacao(efeito_cidade.loc[num_semana, 'variacao_isolamento']).replace('.', ',') + '</i>'] #Variação isolamento
    
    fig = go.Figure(data = [go.Table(header = dict(values = cabecalho,
                                                    fill_color = '#00aabb',
                                                    font = dict(color = 'white'),
                                                    align = ['right', 'right', 'right'],
                                                    line = dict(width = 5)),
                                      cells = dict(values = [info, estado, cidade],
                                                  fill_color = 'lavender',
                                                  align = 'right',
                                                  line = dict(width = 5)),
                                       columnwidth = [1, 1, 1])])
    
    fig.update_layout(
        font = dict(size = 15, family = 'Roboto'),
        margin = dict(l = 1, r = 1, b = 1, t = 30, pad = 5),
        annotations = [dict(x = 0, y = 0, showarrow = False, font = dict(size = 13),
                            text = '<i><b>Fontes:</b> <a href = "https://www.seade.gov.br/coronavirus/">Governo do Estado ' + 
                                    'de São Paulo</a> e <a href = "https://www.prefeitura.sp.gov.br/cidade/secretarias/' +
                                    'saude/vigilancia_em_saude/doencas_e_agravos/coronavirus/index.php?p=295572">Prefeitura' +
                                    ' de São Paulo</a></i>')],
        height = 445
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/resumo-semanal.html', include_plotlyjs = 'directory', auto_open = False)
    
    fig.update_layout(
        font = dict(size = 13),
        margin = dict(l = 1, r = 1, b = 1, t = 30, pad = 5),
        annotations = [dict(x = 0, y = 0)],
        height = 435
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/resumo-semanal-mobile.html', include_plotlyjs = 'directory', auto_open = False)

def gera_casos_estado(dados):
    fig = make_subplots(specs = [[{"secondary_y": True}]])
    
    fig.add_trace(go.Scatter(x = dados['dia'], y = dados['total_casos'], line = dict(color = 'blue'),
                             mode = 'lines+markers', name = 'casos confirmados'))
    
    fig.add_trace(go.Bar(x = dados['dia'], y = dados['casos_dia'], marker_color = 'blue',
                         name = 'casos por dia'))
    
    fig.add_trace(go.Scatter(x = dados['dia'], y = dados['total_obitos'], line = dict(color = 'red'),
                             mode = 'lines+markers', name = 'total de óbitos'))
    
    fig.add_trace(go.Bar(x = dados['dia'], y = dados['obitos_dia'], marker_color = 'red',
                         name = 'óbitos por dia', visible = 'legendonly'))
    
    fig.add_trace(go.Scatter(x = dados['dia'], y = dados['letalidade'], line = dict(color = 'green'),
                             mode = 'lines+markers', name = 'letalidade', hovertemplate = '%{y:.2f}%'),
                  secondary_y = True)
    
    d = dados.dia.size
    
    frames = [dict(data = [dict(type = 'scatter', x = dados.dia[:d+1], y = dados.total_casos[:d+1]),
                           dict(type = 'bar', x = dados.dia[:d+1], y = dados.casos_dia[:d+1]),
                           dict(type = 'scatter', x = dados.dia[:d+1], y = dados.total_obitos[:d+1]),
                           dict(type = 'bar', x = dados.dia[:d+1], y = dados.obitos_dia[:d+1]),
                           dict(type = 'scatter', x = dados.dia[:d+1], y = dados.letalidade[:d+1])],
                   traces = [0, 1, 2, 3, 4],
                  ) for d in range(0, d)]
    
    fig.frames = frames
    
    botoes = [dict(label = 'Animar', method = 'animate',
                   args = [None,dict(frame = dict(duration = 200, redraw = True), fromcurrent = True, mode = 'immediate')])]
    
    fig.update_layout(
        font = dict(family = 'Roboto'),
        title = 'Casos confirmados de Covid-19 no Estado de São Paulo' +
                '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
                'Governo do Estado de São Paulo</a></i>',
        xaxis_tickangle = 45,
        hovermode = 'x unified',
        hoverlabel = {'namelength' : -1}, #para não truncar o nome de cada trace no hover
        template = 'plotly',
        updatemenus = [dict(type = 'buttons', showactive = False,
                            x = 0.05, y = 0.95,
                            xanchor = 'left', yanchor = 'top',
                            pad = dict(t = 0, r = 10), buttons = botoes)]
    )
    
    fig.update_yaxes(title_text = 'Número de casos ou óbitos', secondary_y = False)
    fig.update_yaxes(title_text = 'Taxa de letalidade (%)', secondary_y = True)
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/casos-estado.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
    #versão mobile
    fig.update_traces(selector = dict(type = 'scatter'), mode = 'lines')
    
    fig.update_xaxes(nticks = 10)
    
    fig.update_layout(
        showlegend = False,
        font = dict(size = 11),
        margin = dict(l = 1, r = 1, b = 1, t = 90, pad = 10)
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/casos-estado-mobile.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
def gera_casos_cidade(dados):
    fig = make_subplots(specs = [[{"secondary_y": True}]])
    
    fig.add_trace(go.Scatter(x = dados['dia'], y = dados['suspeitos'], line = dict(color = 'teal'),
                             mode = 'lines+markers', name = 'casos suspeitos', visible = 'legendonly'))
    
    fig.add_trace(go.Bar(x = dados['dia'], y = dados['casos_suspeitos_dia'], marker_color = 'teal',
                         name = 'casos suspeitos por dia', visible = 'legendonly'))
    
    fig.add_trace(go.Scatter(x = dados['dia'], y = dados['confirmados'], line = dict(color = 'blue'),
                             mode = 'lines+markers', name = 'casos confirmados'))
    
    fig.add_trace(go.Bar(x = dados['dia'], y = dados['casos_dia'], marker_color = 'blue',
                         name = 'casos confirmados por dia'))
    
    fig.add_trace(go.Scatter(x = dados['dia'], y = dados['óbitos_suspeitos'], line = dict(color = 'orange'),
                             mode = 'lines+markers', name = 'óbitos suspeitos', visible = 'legendonly'))
    
    fig.add_trace(go.Bar(x = dados['dia'], y = dados['óbitos_suspeitos_dia'], marker_color = 'orange',
                         name = 'óbitos suspeitos por dia', visible = 'legendonly'))
    
    fig.add_trace(go.Scatter(x = dados['dia'], y = dados['óbitos'], line = dict(color = 'red'),
                             mode = 'lines+markers', name = 'óbitos confirmados'))
    
    fig.add_trace(go.Bar(x = dados['dia'], y = dados['óbitos_dia'], marker_color = 'red',
                         name = 'óbitos confirmados por dia', visible = 'legendonly'))
    
    fig.add_trace(go.Scatter(x = dados['dia'], y = dados['letalidade'], line = dict(color = 'green'),
                             mode = 'lines+markers', name = 'letalidade', hovertemplate = '%{y:.2f}%'),
                  secondary_y = True)
    
    d = dados.dia.size
    
    frames = [dict(data = [dict(type = 'scatter', x = dados.dia[:d+1], y = dados.suspeitos[:d+1]),
                           dict(type = 'bar', x = dados.dia[:d+1], y = dados.casos_suspeitos_dia[:d+1]),
                           dict(type = 'scatter', x = dados.dia[:d+1], y = dados.confirmados[:d+1]),
                           dict(type = 'bar', x = dados.dia[:d+1], y = dados.casos_dia[:d+1]),
                           dict(type = 'scatter', x = dados.dia[:d+1], y = dados.óbitos_suspeitos[:d+1]),
                           dict(type = 'bar', x = dados.dia[:d+1], y = dados.óbitos_suspeitos_dia[:d+1]),
                           dict(type = 'scatter', x = dados.dia[:d+1], y = dados.óbitos[:d+1]),
                           dict(type = 'bar', x = dados.dia[:d+1], y = dados.óbitos_dia[:d+1]),
                           dict(type = 'scatter', x = dados.dia[:d+1], y = dados.letalidade[:d+1])],
                   traces = [0, 1, 2, 3, 4, 5, 6, 7, 8],
                  ) for d in range(0, d)]
    
    fig.frames = frames
    
    botoes = [dict(label = 'Animar', method = 'animate',
                   args = [None,dict(frame = dict(duration = 200, redraw = True), fromcurrent = True, mode = 'immediate')])]
    
    fig.update_layout(
        font = dict(family = 'Roboto'),
        title = 'Casos confirmados de Covid-19 na cidade de São Paulo' +
                '<br><i>Fonte: <a href = "https://www.prefeitura.sp.gov.br/cidade/' +
                'secretarias/saude/vigilancia_em_saude/doencas_e_agravos/coronavirus/' +
                'index.php?p=295572">Prefeitura de São Paulo</a></i>',
        xaxis_tickangle = 45,
        hovermode = 'x unified',
        hoverlabel = {'namelength' : -1}, #para não truncar o nome de cada trace no hover
        template = 'plotly',
        updatemenus = [dict(type = 'buttons', showactive = False,
                            x = 0.05, y = 0.95,
                            xanchor = 'left', yanchor = 'top',
                            pad = dict(t = 0, r = 10), buttons = botoes)]
    )
    
    fig.update_yaxes(title_text = 'Número de casos ou óbitos', secondary_y = False)
    fig.update_yaxes(title_text = 'Taxa de letalidade (%)', secondary_y = True)
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/casos-cidade.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
    #versão mobile
    fig.update_traces(selector = dict(type = 'scatter'), mode = 'lines')
    
    fig.update_xaxes(nticks = 10)
    
    fig.update_layout(
        showlegend = False,
        font = dict(size = 11),
        margin = dict(l = 1, r = 1, b = 1, t = 90, pad = 20)
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/casos-cidade-mobile.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
def gera_doencas_preexistentes_casos(doencas):
    idades = list(doencas.reset_index('idade').idade.unique())
    
    casos_ignorados_m = [doencas.xs(('CONFIRMADO', 'FEMININO', i, 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO'), level = ('covid19', 'sexo', 'idade', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica', 'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera', 'sindrome_de_down')).asma.sum() for i in idades]
    casos_ignorados_h = [doencas.xs(('CONFIRMADO', 'MASCULINO', i, 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO'), level = ('covid19', 'sexo', 'idade', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica', 'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera', 'sindrome_de_down')).asma.sum() for i in idades]
    
    casos_sem_doencas_m = [doencas.xs(('CONFIRMADO', 'FEMININO', i, 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO'), level = ('covid19', 'sexo', 'idade', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica', 'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera', 'sindrome_de_down')).asma.sum() for i in idades]
    casos_sem_doencas_h = [doencas.xs(('CONFIRMADO', 'MASCULINO', i, 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO'), level = ('covid19', 'sexo', 'idade', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica', 'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera', 'sindrome_de_down')).asma.sum() for i in idades]
    
    casos_com_doencas_m = []
    casos_com_doencas_h = []
    
    for d in doencas.columns:
        casos_com_doencas_m.append([doencas.xs(('CONFIRMADO', 'FEMININO', i, 'SIM'), level = ('covid19', 'sexo', 'idade', d))[d].sum() for i in idades])
        casos_com_doencas_h.append([doencas.xs(('CONFIRMADO', 'MASCULINO', i, 'SIM'), level = ('covid19', 'sexo', 'idade', d))[d].sum() for i in idades])
     
    #para os dados femininos, todos os valores precisam ser negativados
    casos_ignorados_m_neg = [-valor for valor in casos_ignorados_m]
    casos_sem_doencas_m_neg = [-valor for valor in casos_sem_doencas_m]
    casos_com_doencas_m_neg = [[-valor for valor in lista] for lista in casos_com_doencas_m]
    
    fig = go.Figure()
    
    cont = 0
    
    for lista_m in casos_com_doencas_m_neg:
        fig.add_trace(go.Bar(x = lista_m, y = idades, orientation = 'h',
                             hoverinfo = 'text+y+name', text = casos_com_doencas_m[cont],
                             marker_color = 'red', name = doencas.columns[cont],
                             visible = True if cont == 0 else 'legendonly'))
        cont = cont + 1
    
    cont = 0
    
    for lista_h in casos_com_doencas_h:
        fig.add_trace(go.Bar(x = lista_h, y = idades, orientation = 'h', hoverinfo = 'x+y+name',
                             marker_color = 'blue', name = doencas.columns[cont],
                             visible = True if cont == 0 else 'legendonly'))
        cont = cont + 1
    
    fig.add_trace(go.Bar(x = casos_sem_doencas_m_neg, y = idades, orientation = 'h',
                         hoverinfo = 'text+y+name', text = casos_sem_doencas_m,
                         marker_color = 'red', name = 'sem doenças<br>preexistentes', visible = 'legendonly'))
    
    fig.add_trace(go.Bar(x = casos_sem_doencas_h, y = idades, orientation = 'h', hoverinfo = 'x+y+name',
                         marker_color = 'blue', name = 'sem doenças<br>preexistentes', visible = 'legendonly'))
    
    fig.add_trace(go.Bar(x = casos_ignorados_m_neg, y = idades, orientation = 'h',
                         hoverinfo = 'text+y+name', text = casos_ignorados_m,
                         marker_color = 'red', name = 'ignorado', visible = 'legendonly'))
    
    fig.add_trace(go.Bar(x = casos_ignorados_h, y = idades, orientation = 'h', hoverinfo = 'x+y+name',
                         marker_color = 'blue', name = 'ignorado', visible = 'legendonly'))
    
    fig.update_layout(
        font = dict(family = 'Roboto'),
        title = 'Doenças preexistentes nos casos confirmados de Covid-19 no Estado de São Paulo' +
                '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
                'Governo do Estado de São Paulo</a></i>',
        yaxis_title = 'Idade',
        xaxis_title = 'Mulheres | Homens',
        hovermode = 'y',
        hoverlabel = {'namelength' : -1}, #para não truncar o nome de cada trace no hover
        template = 'plotly',
        barmode = 'overlay',
        bargap = 0.1
    )
    
    fig.update_yaxes(range = [0, 105], tickvals = [*range(0, 105, 5)])
    
    pio.write_html(fig, file = 'docs/graficos/doencas-casos.html', include_plotlyjs = 'directory',
                   auto_open = False, auto_play = False)
    
    #versão mobile
    fig.update_yaxes(range = [0, 105], tickvals = [*range(0, 105, 10)])
        
    fig.update_layout(
        font = dict(size = 11),
        margin = dict(l = 1, r = 1, b = 1, t = 90, pad = 10)
    )
    
    pio.write_html(fig, file = 'docs/graficos/doencas-casos-mobile.html', include_plotlyjs = 'directory',
                   auto_open = False, auto_play = False)

def gera_doencas_preexistentes_obitos(doencas):
    idades = list(doencas.reset_index('idade').idade.unique())
    
    obitos_ignorados_m = [doencas.xs(('CONFIRMADO', 'FEMININO', i, 1, 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO'), level = ('covid19', 'sexo', 'idade', 'obito', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica', 'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera', 'sindrome_de_down')).asma.sum() for i in idades]
    obitos_ignorados_h = [doencas.xs(('CONFIRMADO', 'MASCULINO', i, 1, 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO'), level = ('covid19', 'sexo', 'idade', 'obito', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica', 'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera', 'sindrome_de_down')).asma.sum() for i in idades]
    
    obitos_sem_doencas_m = [doencas.xs(('CONFIRMADO', 'FEMININO', i, 1, 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO'), level = ('covid19', 'sexo', 'idade', 'obito', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica', 'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera', 'sindrome_de_down')).asma.sum() for i in idades]
    obitos_sem_doencas_h = [doencas.xs(('CONFIRMADO', 'MASCULINO', i, 1, 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO'), level = ('covid19', 'sexo', 'idade', 'obito', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica', 'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera', 'sindrome_de_down')).asma.sum() for i in idades]
    
    obitos_com_doencas_m = []
    obitos_com_doencas_h = []
    
    for d in doencas.columns:
        obitos_com_doencas_m.append([doencas.xs(('CONFIRMADO', 'FEMININO', i, 1, 'SIM'), level = ('covid19', 'sexo', 'idade', 'obito', d))[d].sum() for i in idades])
        obitos_com_doencas_h.append([doencas.xs(('CONFIRMADO', 'MASCULINO', i, 1, 'SIM'), level = ('covid19', 'sexo', 'idade', 'obito', d))[d].sum() for i in idades])
     
    #para os dados femininos, todos os valores precisam ser negativados
    obitos_ignorados_m_neg = [-valor for valor in obitos_ignorados_m]
    obitos_sem_doencas_m_neg = [-valor for valor in obitos_sem_doencas_m]
    obitos_com_doencas_m_neg = [[-valor for valor in lista] for lista in obitos_com_doencas_m]
    
    fig = go.Figure()
    
    cont = 0
    
    for lista_m in obitos_com_doencas_m_neg:
        fig.add_trace(go.Bar(x = lista_m, y = idades, orientation = 'h',
                             hoverinfo = 'text+y+name', text = obitos_com_doencas_m[cont],
                             marker_color = 'red', name = doencas.columns[cont],
                             visible = True if cont == 0 else 'legendonly'))
        cont = cont + 1
    
    cont = 0
    
    for lista_h in obitos_com_doencas_h:
        fig.add_trace(go.Bar(x = lista_h, y = idades, orientation = 'h', hoverinfo = 'x+y+name',
                             marker_color = 'blue', name = doencas.columns[cont],
                             visible = True if cont == 0 else 'legendonly'))
        cont = cont + 1
    
    fig.add_trace(go.Bar(x = obitos_sem_doencas_m_neg, y = idades, orientation = 'h',
                         hoverinfo = 'text+y+name', text = obitos_sem_doencas_m,
                         marker_color = 'red', name = 'sem doenças<br>preexistentes', visible = 'legendonly'))
    
    fig.add_trace(go.Bar(x = obitos_sem_doencas_h, y = idades, orientation = 'h', hoverinfo = 'x+y+name',
                         marker_color = 'blue', name = 'sem doenças<br>preexistentes', visible = 'legendonly'))
    
    fig.add_trace(go.Bar(x = obitos_ignorados_m_neg, y = idades, orientation = 'h',
                         hoverinfo = 'text+y+name', text = obitos_ignorados_m,
                         marker_color = 'red', name = 'ignorado', visible = 'legendonly'))
    
    fig.add_trace(go.Bar(x = obitos_ignorados_h, y = idades, orientation = 'h', hoverinfo = 'x+y+name',
                         marker_color = 'blue', name = 'ignorado', visible = 'legendonly'))
    
    fig.update_layout(
        font = dict(family = 'Roboto'),
        title = 'Doenças preexistentes nos óbitos confirmados por Covid-19 no Estado de São Paulo' +
                '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
                'Governo do Estado de São Paulo</a></i>',
        yaxis_title = 'Idade',
        xaxis_title = 'Mulheres | Homens',
        hovermode = 'y',
        hoverlabel = {'namelength' : -1}, #para não truncar o nome de cada trace no hover
        template = 'plotly',
        barmode = 'overlay',
        bargap = 0.1
    )
    
    fig.update_yaxes(range = [0, 105], tickvals = [*range(0, 105, 5)])
    
    pio.write_html(fig, file = 'docs/graficos/doencas-obitos.html', include_plotlyjs = 'directory',
                   auto_open = False, auto_play = False)
    
    #versão mobile
    fig.update_yaxes(range = [0, 105], tickvals = [*range(0, 105, 10)])
        
    fig.update_layout(
        font = dict(size = 11),
        margin = dict(l = 1, r = 1, b = 1, t = 90, pad = 10)
    )
    
    pio.write_html(fig, file = 'docs/graficos/doencas-obitos-mobile.html', include_plotlyjs = 'directory',
                   auto_open = False, auto_play = False)

def gera_casos_obitos_por_raca_cor(dados_raciais):
    racas_cores = list(dados_raciais.reset_index('raca_cor').raca_cor.unique())
    
    casos = [dados_raciais.xs((rc), level = ('raca_cor')).contagem.sum() for rc in racas_cores]
    casos_perc = ['{:02.1f}%'.format((c / sum(casos))* 100) for c in casos]
    
    obitos = [dados_raciais.xs((1, rc), level = ('obito', 'raca_cor')).contagem.sum() for rc in racas_cores]
    obitos_perc = ['{:02.1f}%'.format((o / sum(obitos)) * 100) for o in obitos]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(x = casos, y = racas_cores,
                         orientation = 'h', hoverinfo = 'x+y+name',
                         textposition = 'auto', text = casos_perc,
                         marker_color = 'blue', name = 'casos', visible = True))
    
    fig.add_trace(go.Bar(x = obitos, y = racas_cores,
                         orientation = 'h', hoverinfo = 'x+y+name',
                         textposition = 'auto', text = obitos_perc,
                         marker_color = 'red', name = 'óbitos', visible = True))
    
    fig.update_layout(
        font = dict(family = 'Roboto'),
        title = 'Raça/cor nos casos e óbitos confirmados por Covid-19 no Estado de São Paulo' +
                '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
                'Governo do Estado de São Paulo</a></i>',
        xaxis_title = 'Casos ou óbitos',
        xaxis_tickangle = 30,
        hovermode = 'y',
        barmode = 'stack',
        bargap = 0.1,
        hoverlabel = {'namelength' : -1},
        template = 'plotly'
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/raca-cor.html', include_plotlyjs = 'directory',
                   auto_open = False, auto_play = False)
    
    #versão mobile        
    fig.update_layout(
        font = dict(size = 11),
        margin = dict(l = 1, r = 1, b = 1, t = 90, pad = 10)
    )
    
    pio.write_html(fig, file = 'docs/graficos/raca-cor-mobile.html', include_plotlyjs = 'directory',
                   auto_open = False, auto_play = False)
    
def gera_isolamento_grafico(isolamento):
    fig = go.Figure()

    #lista de municípios em ordem de maior índice de isolamento
    l_municipios = list(isolamento.sort_values(by = ['data', 'isolamento', 'município'], ascending = False).município.unique())
    
    #series em vez de list, para que seja possível utilizar o método isin
    s_municipios = pd.Series(l_municipios)
    
    titulo_a = 'Índice de adesão ao isolamento social - '
    titulo_b = '<br><i>Fonte: <a href = "https://www.saopaulo.sp.gov.br/coronavirus/isolamento/">Governo do Estado de São Paulo</a></i>'
    
    cidades_iniciais = ['Estado de São Paulo', 'São Paulo', 'Guarulhos', 'Osasco', 'Jundiaí', 'Caieiras', 
                        'Campinas', 'Santo André', 'Mauá', 'Francisco Morato', 'Poá']
    
    for m in l_municipios:
        grafico = isolamento[isolamento.município == m]
        
        if m in cidades_iniciais:
            fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['isolamento'], name = m,
                                     mode = 'lines+markers', hovertemplate = '%{y:.0f}%', visible = True))
        else:
            fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['isolamento'], name = m,
                                     mode = 'lines+markers+text', textposition = 'top center', 
                                     text = grafico['isolamento'].apply(lambda i: str(i) + '%'), hovertemplate = '%{y:.0f}%', visible = False))
            
    opcao_metro = dict(label = 'Região Metropolitana',
                        method = 'update',
                        args = [{'visible': s_municipios.isin(cidades_iniciais)},
                                {'title.text': titulo_a + 'Região Metropolitana' + titulo_b},
                                {'showlegend': True}])
    
    opcao_estado = dict(label = 'Estado de São Paulo',
                        method = 'update',
                        args = [{'visible': s_municipios.isin(['Estado de São Paulo'])},
                                {'title.text': titulo_a + 'Estado de São Paulo' + titulo_b},
                                {'showlegend': False}])
    
    def cria_lista_opcoes(cidade):
        return dict(label = cidade,
                    method = 'update',
                    args = [{'visible': s_municipios.isin([cidade])},
                            {'title.text': titulo_a + cidade + titulo_b},
                            {'showlegend': False}])
        
    fig.update_layout(
        font = dict(family = 'Roboto'),
        title = titulo_a + 'Região Metropolitana' + titulo_b,
        xaxis_tickangle = 45,
        yaxis_title = 'Índice de isolamento social (%)',
        hovermode = 'x unified',
        hoverlabel = {'namelength' : -1}, #para não truncar o nome de cada trace no hover
        template = 'plotly',
        updatemenus = [go.layout.Updatemenu(active = 0,
                                            buttons = [opcao_metro, opcao_estado] + list(s_municipios.apply(lambda m: cria_lista_opcoes(m))),
                                            x = 0.001, xanchor = 'left',
                                            y = 0.990, yanchor = 'top')]
    )
        
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/isolamento.html', include_plotlyjs = 'directory', auto_open = False)
    
    #versão mobile
    fig.update_traces(mode = 'lines+text')
    
    fig.update_xaxes(nticks = 10)
        
    fig.update_layout(
        showlegend = False,
        font = dict(size = 11),
        margin = dict(l = 1, r = 1, b = 1, t = 90, pad = 10)
    )
        
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/isolamento-mobile.html', include_plotlyjs = 'directory', auto_open = False)

def gera_isolamento_tabela(isolamento):
    dados = isolamento.loc[isolamento.data == isolamento.data.max(), ['data', 'município', 'isolamento']]
    dados.sort_values(by = ['isolamento', 'município'], ascending = False, inplace = True)
    
    cabecalho = ['<b>Cidade</b>', 
                 '<b>Isolamento</b><br><i>' + dados.data.iloc[0].strftime('%d/%m/%Y') + '</i>']
    
    fig = go.Figure(data = [go.Table(header = dict(values = cabecalho,
                                                   fill_color = '#00aabb',
                                                   font = dict(color = 'white'),
                                                   align = 'right',
                                                   line = dict(width = 5)),
                                     cells = dict(values = [dados.município, dados.isolamento.map('{:02.0f}%'.format)],
                                                  fill_color = 'lavender',
                                                  align = 'right',
                                                  line = dict(width = 5),
                                                  height = 30),
                                     columnwidth = [1, 1])])
    
    fig.update_layout(
        font = dict(size = 15, family = 'Roboto'),
        margin = dict(l = 1, r = 1, b = 1, t = 30, pad = 5),
        annotations = [dict(x = 0, y = 0, showarrow = False, font = dict(size = 13),
                            text = '<i><b>Fonte:</b> <a href = "https://www.saopaulo.sp.gov.br/coronavirus/isolamento/">'
                                   'Governo do Estado de São Paulo</a></i>')]
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/tabela-isolamento.html', include_plotlyjs = 'directory', auto_open = False)
    
    fig.update_layout(
        font = dict(size = 13),
        margin = dict(l = 1, r = 1, b = 1, t = 30, pad = 5),
        annotations = [dict(x = 0, y = 0)]
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/tabela-isolamento-mobile.html', include_plotlyjs = 'directory', auto_open = False)
    
def gera_efeito_estado(efeito_estado):        
    fig = make_subplots(specs = [[{"secondary_y": True}]])

    grafico = efeito_estado
    
    fig.add_trace(go.Scatter(x = grafico['data'], y = grafico['isolamento'], line = dict(color = 'orange'),
                             name = 'isolamento médio<br>de 2 semanas atrás', hovertemplate = '%{y:.2f}%',
                             mode = 'lines+markers+text', textposition = 'top center',
                             text = grafico['variacao_isolamento_2sem'].apply(lambda v: _formata_variacao(v))),
                  secondary_y = True)
    
    fig.add_trace(go.Scatter(x = grafico['data'], y = grafico['uti'], line = dict(color = 'green'),
                             name = 'taxa média de<br>ocupação de UTI', hovertemplate = '%{y:.2f}%',
                             mode = 'lines+markers+text', textposition = 'top center',
                             text = grafico['variacao_uti'].apply(lambda v: _formata_variacao(v)),
                             visible = 'legendonly'),
                  secondary_y = True)
    
    fig.add_trace(go.Bar(x = grafico['data'], y = grafico['casos_semana'], marker_color = 'blue',
                         name = 'casos na<br>semana atual', textposition = 'outside',
                         text = grafico['variacao_casos'].apply(lambda v: _formata_variacao(v))))
    
    fig.add_trace(go.Bar(x = grafico['data'], y = grafico['obitos_semana'], marker_color = 'red',
                         name = 'óbitos na<br>semana atual', textposition = 'outside',
                         text = grafico['variacao_obitos'].apply(lambda v: _formata_variacao(v))))
    
    d = grafico.data.size
    
    frames = [dict(data = [dict(type = 'scatter', x = grafico.data[:d+1], y = grafico.isolamento[:d+1]),
                           dict(type = 'scatter', x = grafico.data[:d+1], y = grafico.uti[:d+1]),
                           dict(type = 'bar', x = grafico.data[:d+1], y = grafico.casos_semana[:d+1]),
                           dict(type = 'bar', x = grafico.data[:d+1], y = grafico.obitos_semana[:d+1])],
                   traces = [0, 1, 2, 3],
                  ) for d in range(0, d)]
    
    fig.frames = frames
    
    botoes = [dict(label = 'Animar', method = 'animate',
                   args = [None,dict(frame = dict(duration = 400, redraw = True), fromcurrent = True, mode = 'immediate')])]
    
    fig.update_yaxes(title_text = 'Número de casos ou óbitos', secondary_y = False)
    fig.update_yaxes(title_text = 'Taxa média de isolamento há 2 semanas (%)', secondary_y = True)
    
    fig.update_layout(
        font = dict(family = 'Roboto'),
        title = 'Efeito do isolamento social no Estado de São Paulo' +
                '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
                'Governo do Estado de São Paulo</a></i>',
        xaxis_tickangle = 30,
        hovermode = 'x unified',
        hoverlabel = {'namelength' : -1},
        template = 'plotly',
        updatemenus = [dict(type = 'buttons', showactive = False,
                            x = 0.05, y = 0.95,
                            xanchor = 'left', yanchor = 'top',
                            pad = dict(t = 0, r = 10), buttons = botoes)]
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/efeito-estado.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
    #versão mobile
    fig.update_traces(selector = dict(type = 'scatter'), mode = 'lines')
    
    fig.update_xaxes(nticks = 10)
        
    fig.update_layout(
        showlegend = False,
        font = dict(size = 11),
        margin = dict(l = 1, r = 1, b = 1, t = 90, pad = 10)
    )
        
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/efeito-estado-mobile.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
def gera_efeito_cidade(efeito_cidade):
    fig = make_subplots(specs = [[{"secondary_y": True}]])
    
    grafico = efeito_cidade
    
    fig.add_trace(go.Scatter(x = grafico['data'], y = grafico['isolamento'], line = dict(color = 'orange'),
                             name = 'isolamento médio<br>de 2 semanas atrás', hovertemplate = '%{y:.2f}%',
                             mode = 'lines+markers+text', textposition = 'top center',
                             text = grafico['variacao_isolamento_2sem'].apply(lambda v: _formata_variacao(v))),
                  secondary_y = True)
    
    fig.add_trace(go.Scatter(x = grafico['data'], y = grafico['uti'], line = dict(color = 'green'),
                             name = 'taxa média de<br>ocupação de UTI', hovertemplate = '%{y:.2f}%',
                             mode = 'lines+markers+text', textposition = 'top center',
                             text = grafico['variacao_uti'].apply(lambda v: _formata_variacao(v)),
                             visible = 'legendonly'),
                  secondary_y = True)
    
    fig.add_trace(go.Bar(x = grafico['data'], y = grafico['casos_semana'], marker_color = 'blue',
                         name = 'casos na<br>semana atual', textposition = 'outside',
                         text = grafico['variacao_casos'].apply(lambda v: _formata_variacao(v))))
    
    fig.add_trace(go.Bar(x = grafico['data'], y = grafico['obitos_semana'], marker_color = 'red',
                         name = 'óbitos na<br>semana atual', textposition = 'outside',
                         text = grafico['variacao_obitos'].apply(lambda v: _formata_variacao(v))))
    
    d = grafico.data.size
    
    frames = [dict(data = [dict(type = 'scatter', x = grafico.data[:d+1], y = grafico.isolamento[:d+1]),
                           dict(type = 'scatter', x = grafico.data[:d+1], y = grafico.uti[:d+1]),
                           dict(type = 'bar', x = grafico.data[:d+1], y = grafico.casos_semana[:d+1]),
                           dict(type = 'bar', x = grafico.data[:d+1], y = grafico.obitos_semana[:d+1])],
                   traces = [0, 1, 2, 3],
                  ) for d in range(0, d)]
    
    fig.frames = frames
    
    botoes = [dict(label = 'Animar', method = 'animate',
                   args = [None,dict(frame = dict(duration = 400, redraw = True), fromcurrent = True, mode = 'immediate')])]
    
    fig.update_yaxes(title_text = 'Número de casos ou óbitos', secondary_y = False)
    fig.update_yaxes(title_text = 'Taxa média de isolamento há 2 semanas (%)', secondary_y = True)
    
    fig.update_layout(
        font = dict(family = 'Roboto'),
        title = 'Efeito do isolamento social na Cidade de São Paulo' +
                '<br><i>Fonte: <a href = "https://www.prefeitura.sp.gov.br/cidade/' +
                'secretarias/saude/vigilancia_em_saude/doencas_e_agravos/coronavirus/' +
                'index.php?p=295572">Prefeitura de São Paulo</a></i>',
        xaxis_tickangle = 30,
        hovermode = 'x unified',
        hoverlabel = {'namelength' : -1},
        template = 'plotly',
        updatemenus = [dict(type = 'buttons', showactive = False,
                            x = 0.05, y = 0.95,
                            xanchor = 'left', yanchor = 'top',
                            pad = dict(t = 0, r = 10), buttons = botoes)]
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/efeito-cidade.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
    #versão mobile
    fig.update_traces(selector = dict(type = 'scatter'), mode = 'lines')
    
    fig.update_xaxes(nticks = 10)
        
    fig.update_layout(
        showlegend = False,
        font = dict(size = 11),
        margin = dict(l = 1, r = 1, b = 1, t = 90, pad = 10)
    )
        
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/efeito-cidade-mobile.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
def gera_leitos_estaduais(leitos):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['rmsp_uti'],
                             mode = 'lines+markers', name = 'UTI<br>(região metropolitana)', 
                             hovertemplate = '%{y:.1f}%'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['rmsp_enfermaria'],
                             mode = 'lines+markers', name = 'enfermaria<br>(região metropolitana)', 
                             hovertemplate = '%{y:.1f}%'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['sp_uti'],
                             mode = 'lines+markers', name = 'UTI<br>(estado)', hovertemplate = '%{y:.1f}%'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['sp_enfermaria'],
                             mode = 'lines+markers', name = 'enfermaria<br>(estado)', hovertemplate = '%{y:.1f}%'))
    
    d = leitos.dia.size
    
    frames = [dict(data = [dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.rmsp_uti[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.rmsp_enfermaria[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.sp_uti[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.sp_enfermaria[:d+1])],
                   traces = [0, 1, 2, 3],
                  ) for d in range(0, d)]
    
    fig.frames = frames
    
    botoes = [dict(label = 'Animar', method = 'animate',
                   args = [None,dict(frame = dict(duration = 200, redraw = True), fromcurrent = True, mode = 'immediate')])]
    
    fig.update_layout(
        font = dict(family = 'Roboto'),
        title = 'Ocupação de leitos Covid-19 no Estado de São Paulo' +
                '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
                'Governo do Estado de São Paulo</a></i>',
        xaxis_tickangle = 45,
        yaxis_title = 'Taxa de ocupação dos leitos (%)',
        hovermode = 'x unified',
        hoverlabel = {'namelength' : -1}, #para não truncar o nome de cada trace no hover
        template = 'plotly',
        updatemenus = [dict(type = 'buttons', showactive = False,
                            x = 0.05, y = 0.95,
                            xanchor = 'left', yanchor = 'top',
                            pad = dict(t = 0, r = 10), buttons = botoes)]
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/leitos-estaduais.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
    #versão mobile
    fig.update_traces(mode = 'lines')
    
    fig.update_xaxes(nticks = 10)
    
    fig.update_layout(
        showlegend = False,
        font = dict(size = 11),
        margin = dict(l = 1, r = 1, b = 1, t = 90, pad = 10)
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/leitos-estaduais-mobile.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)

def gera_drs(internacoes):
    fig = make_subplots(specs = [[{"secondary_y": True}]])

    #lista de Departamentos Regionais de Saúde
    l_drs = list(internacoes.drs.sort_values(ascending = False).unique())
    
    #series em vez de list, para que seja possível utilizar o método isin
    s_drs = pd.Series(l_drs)
    
    titulo_a = 'Departamento Regional de Saúde - '
    titulo_b = '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">Governo do Estado de São Paulo</a></i>'
        
    for d in l_drs:
        grafico = internacoes[internacoes.drs == d]
        
        if d == 'Estado de São Paulo':
            mostrar = True
        else:
            mostrar = False
        
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['pacientes_uti_mm7d'], name = 'pacientes internados em leitos<br>de UTI para Covid-19 - média<br>móvel dos últimos 7 dias',
                                 mode = 'lines+markers', hovertemplate = '%{y:.0f}', customdata = [d], visible = mostrar))
        
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['total_covid_uti_mm7d'], name = 'leitos Covid-19 - média<br>móvel dos últimos 7 dias',
                                 mode = 'lines+markers', hovertemplate = '%{y:.0f}', customdata = [d], visible = mostrar))
        
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['ocupacao_leitos'], name = 'ocupação de leitos de<br>UTI para Covid-19',
                                 mode = 'lines+markers', hovertemplate = '%{y:.2f}%', customdata = [d], visible = mostrar),
                      secondary_y = True)
        
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['leitos_pc'], name = 'leitos Covid-19 para<br>cada 100 mil habitantes',
                                 mode = 'lines+markers', customdata = [d], visible = mostrar))
        
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['internacoes_7d'], name = 'internações (UTI e enfermaria,<br>confirmados e suspeitos)<br>média móvel dos últimos 7 dias',
                                 mode = 'lines+markers', customdata = [d], visible = mostrar))
        
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['internacoes_7d_l'], name = 'internações (UTI e enfermaria,<br>confirmados e suspeitos)<br>média móvel dos 7 dias<br>anteriores',
                                 mode = 'lines+markers', customdata = [d], visible = mostrar))
        
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['internacoes_7v7'], name = 'variação do número<br>de internações',
                                 mode = 'lines+markers', hovertemplate = '%{y:.1f}%', customdata = [d], visible = mostrar),
                      secondary_y = True)
    
    def cria_lista_opcoes(drs):
        return dict(label = drs,
                    method = 'update',
                    args = [{'visible': [True if drs in trace['customdata'] else False for trace in fig._data]},
                            {'title.text': titulo_a + drs + titulo_b},
                            {'showlegend': True}])
        
    fig.update_layout(
        font = dict(family = 'Roboto'),
        title = titulo_a + 'Estado de São Paulo' + titulo_b,
        xaxis_tickangle = 45,
        hovermode = 'x unified',
        hoverlabel = {'namelength' : -1}, #para não truncar o nome de cada trace no hover
        template = 'plotly',
        updatemenus = [go.layout.Updatemenu(active = 6,
                                            showactive = True,
                                            buttons = list(s_drs.apply(lambda d: cria_lista_opcoes(d))),
                                            x = 0.001, xanchor = 'left',
                                            y = 0.990, yanchor = 'top')]
    )
    
    fig.update_yaxes(title_text = 'Número de leitos ou internações', secondary_y = False)
    fig.update_yaxes(title_text = 'Variação de internações (%)', secondary_y = True)
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/drs.html', include_plotlyjs = 'directory', auto_open = False)
    
    #versão mobile
    fig.update_traces(mode = 'lines+text')
    
    fig.update_xaxes(nticks = 10)
        
    fig.update_layout(
        showlegend = False,
        font = dict(size = 11),
        margin = dict(l = 1, r = 1, b = 1, t = 90, pad = 10)
    )
        
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/drs-mobile.html', include_plotlyjs = 'directory', auto_open = False)

def gera_leitos_municipais(leitos):
    fig = make_subplots(specs = [[{"secondary_y": True}]])
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['ocupacao_uti_covid_publico'],
                             mode = 'lines+markers', name = 'taxa de ocupação de<br>leitos UTI Covid',
                             hovertemplate = '%{y:.0f}%'),
                  secondary_y = True)
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['uti_covid_publico'],
                             mode = 'lines+markers', name = 'leitos UTI Covid em operação'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['internados_uti_publico'],
                             mode = 'lines+markers', name = 'pacientes internados em<br>leitos UTI Covid'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['ventilacao_publico'], visible = 'legendonly',
                             mode = 'lines+markers', name = 'pacientes internados em<br>ventilação mecânica'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['internados_publico'], visible = 'legendonly',
                             mode = 'lines+markers', name = 'total de pacientes internados'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['respiratorio_publico'], visible = 'legendonly',
                             mode = 'lines+markers', name = 'pacientes atendidos com<br>quadro respiratório'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['suspeitos_publico'], visible = 'legendonly',
                             mode = 'lines+markers', name = 'pacientes atendidos com<br>suspeita de Covid-19'))
    
    d = leitos.dia.size
    
    frames = [dict(data = [dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.ocupacao_uti_covid_publico[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.uti_covid_publico[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.internados_uti_publico[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.ventilacao_publico[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.internados_publico[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.respiratorio_publico[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.suspeitos_publico[:d+1])],
                   traces = [0, 1, 2, 3, 4, 5, 6],
                  ) for d in range(0, d)]
    
    fig.frames = frames
    
    botoes = [dict(label = 'Animar', method = 'animate',
                   args = [None,dict(frame = dict(duration = 200, redraw = True), fromcurrent = True, mode = 'immediate')])]
    
    fig.update_layout(
        font = dict(family = 'Roboto'),
        title = 'Situação dos 20 Hospitais Públicos Municipais' + 
                '<br><i>Fonte: <a href = "https://www.prefeitura.sp.gov.br/cidade/' +
                'secretarias/saude/vigilancia_em_saude/doencas_e_agravos/coronavirus/' +
                'index.php?p=295572">Prefeitura de São Paulo</a></i>',
        xaxis_tickangle = 45,
        hovermode = 'x unified',
        hoverlabel = {'namelength' : -1}, #para não truncar o nome de cada trace no hover
        template = 'plotly',
        showlegend = True,
        updatemenus = [dict(type = 'buttons', showactive = False,
                            x = 0.05, y = 0.95,
                            xanchor = 'left', yanchor = 'top',
                            pad = dict(t = 0, r = 10), buttons = botoes)]
    )
    
    fig.update_yaxes(title_text = 'Número de pacientes', secondary_y = False)
    fig.update_yaxes(title_text = 'Taxa de ocupação de UTI (%)', secondary_y = True)
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/leitos-municipais.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
    #versão mobile
    fig.update_traces(mode = 'lines')
    
    fig.update_xaxes(nticks = 10)
    
    fig.update_layout(
        font = dict(size = 11),
        margin = dict(l = 1, r = 1, b = 1, t = 90, pad = 20),
        showlegend = False
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/leitos-municipais-mobile.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
def gera_leitos_municipais_privados(leitos):
    fig = make_subplots(specs = [[{"secondary_y": True}]])
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['ocupacao_uti_covid_privado'],
                             mode = 'lines+markers', name = 'taxa de ocupação de<br>leitos UTI Covid',
                             hovertemplate = '%{y:.0f}%'),
                  secondary_y = True)
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['uti_covid_privado'],
                             mode = 'lines+markers', name = 'leitos UTI Covid em operação'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['internados_uti_privado'],
                             mode = 'lines+markers', name = 'pacientes internados em<br>leitos UTI Covid'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['ventilacao_privado'], visible = 'legendonly',
                             mode = 'lines+markers', name = 'pacientes internados em<br>ventilação mecânica'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['internados_privado'], visible = 'legendonly',
                             mode = 'lines+markers', name = 'total de pacientes internados'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['respiratorio_privado'], visible = 'legendonly',
                             mode = 'lines+markers', name = 'pacientes atendidos com<br>quadro respiratório'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['suspeitos_privado'], visible = 'legendonly',
                             mode = 'lines+markers', name = 'pacientes atendidos com<br>suspeita de Covid-19'))
    
    d = leitos.dia.size
    
    frames = [dict(data = [dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.ocupacao_uti_covid_privado[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.uti_covid_privado[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.internados_uti_privado[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.ventilacao_privado[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.internados_privado[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.respiratorio_privado[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.suspeitos_privado[:d+1])],
                   traces = [0, 1, 2, 3, 4, 5, 6],
                  ) for d in range(0, d)]
    
    fig.frames = frames
    
    botoes = [dict(label = 'Animar', method = 'animate',
                   args = [None,dict(frame = dict(duration = 200, redraw = True), fromcurrent = True, mode = 'immediate')])]
    
    fig.update_layout(
        font = dict(family = 'Roboto'),
        title = 'Situação dos leitos privados contratados pela Prefeitura' + 
                '<br><i>Fonte: <a href = "https://www.prefeitura.sp.gov.br/cidade/' +
                'secretarias/saude/vigilancia_em_saude/doencas_e_agravos/coronavirus/' +
                'index.php?p=295572">Prefeitura de São Paulo</a></i>',
        xaxis_tickangle = 45,
        hovermode = 'x unified',
        hoverlabel = {'namelength' : -1}, #para não truncar o nome de cada trace no hover
        template = 'plotly',
        showlegend = True,
        updatemenus = [dict(type = 'buttons', showactive = False,
                            x = 0.05, y = 0.95,
                            xanchor = 'left', yanchor = 'top',
                            pad = dict(t = 0, r = 10), buttons = botoes)]
    )
    
    fig.update_yaxes(title_text = 'Número de pacientes', secondary_y = False)
    fig.update_yaxes(title_text = 'Taxa de ocupação de UTI (%)', secondary_y = True)
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/leitos-municipais-privados.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
    #versão mobile
    fig.update_traces(mode = 'lines')
    
    fig.update_xaxes(nticks = 10)
    
    fig.update_layout(
        font = dict(size = 11),
        margin = dict(l = 1, r = 1, b = 1, t = 90, pad = 20),
        showlegend = False
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/leitos-municipais-privados-mobile.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
def gera_leitos_municipais_total(leitos):
    fig = make_subplots(specs = [[{"secondary_y": True}]])
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['ocupacao_uti_covid_total'],
                             mode = 'lines+markers', name = 'taxa de ocupação de<br>leitos UTI Covid',
                             hovertemplate = '%{y:.0f}%'),
                  secondary_y = True)
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['uti_covid_total'],
                             mode = 'lines+markers', name = 'leitos UTI Covid em operação'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['internados_uti_total'],
                             mode = 'lines+markers', name = 'pacientes internados em<br>leitos UTI Covid'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['ventilacao_total'], visible = 'legendonly',
                             mode = 'lines+markers', name = 'pacientes internados em<br>ventilação mecânica'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['internados_total'], visible = 'legendonly',
                             mode = 'lines+markers', name = 'total de pacientes internados'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['respiratorio_total'], visible = 'legendonly',
                             mode = 'lines+markers', name = 'pacientes atendidos com<br>quadro respiratório'))
    
    fig.add_trace(go.Scatter(x = leitos['dia'], y = leitos['suspeitos_total'], visible = 'legendonly',
                             mode = 'lines+markers', name = 'pacientes atendidos com<br>suspeita de Covid-19'))
    
    d = leitos.dia.size
    
    frames = [dict(data = [dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.ocupacao_uti_covid_total[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.uti_covid_total[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.internados_uti_total[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.ventilacao_total[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.internados_total[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.respiratorio_total[:d+1]),
                           dict(type = 'scatter', x = leitos.dia[:d+1], y = leitos.suspeitos_total[:d+1])],
                   traces = [0, 1, 2, 3, 4, 5, 6],
                  ) for d in range(0, d)]
    
    fig.frames = frames
    
    botoes = [dict(label = 'Animar', method = 'animate',
                   args = [None,dict(frame = dict(duration = 200, redraw = True), fromcurrent = True, mode = 'immediate')])]
    
    fig.update_layout(
        font = dict(family = 'Roboto'),
        title = 'Situação geral dos leitos públicos e privados' + 
                '<br><i>Fonte: <a href = "https://www.prefeitura.sp.gov.br/cidade/' +
                'secretarias/saude/vigilancia_em_saude/doencas_e_agravos/coronavirus/' +
                'index.php?p=295572">Prefeitura de São Paulo</a></i>',
        xaxis_tickangle = 45,
        hovermode = 'x unified',
        hoverlabel = {'namelength' : -1}, #para não truncar o nome de cada trace no hover
        template = 'plotly',
        showlegend = True,
        updatemenus = [dict(type = 'buttons', showactive = False,
                            x = 0.05, y = 0.95,
                            xanchor = 'left', yanchor = 'top',
                            pad = dict(t = 0, r = 10), buttons = botoes)]
    )
    
    fig.update_yaxes(title_text = 'Número de pacientes', secondary_y = False)
    fig.update_yaxes(title_text = 'Taxa de ocupação de UTI (%)', secondary_y = True)
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/leitos-municipais-total.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
    #versão mobile
    fig.update_traces(mode = 'lines')
    
    fig.update_xaxes(nticks = 10)
    
    fig.update_layout(
        font = dict(size = 11),
        margin = dict(l = 1, r = 1, b = 1, t = 90, pad = 20),
        showlegend = False
    )
    
    # fig.show()
    
    pio.write_html(fig, file = 'docs/graficos/leitos-municipais-total-mobile.html',
                   include_plotlyjs = 'directory', auto_open = False, auto_play = False)
    
def gera_hospitais_campanha(hospitais_campanha):
    for h in hospitais_campanha.hospital.unique():
        grafico = hospitais_campanha[hospitais_campanha.hospital == h]
        
        fig = go.Figure()
    
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['comum'],
                                 mode = 'lines+markers', name = 'leitos de enfermaria'))
    
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['ocupação_comum'],
                                 mode = 'lines+markers', name = 'internados em leitos<br>de enfermaria'))
    
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['uti'],
                                 mode = 'lines+markers', name = 'leitos de estabilização'))
    
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['ocupação_uti'],
                                 mode = 'lines+markers', name = 'internados em leitos<br>de estabilização'))
        
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['altas'],
                                 mode = 'lines+markers', name = 'altas', visible = 'legendonly'))
        
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['óbitos'],
                                 mode = 'lines+markers', name = 'óbitos', visible = 'legendonly'))
        
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['transferidos'],
                                 mode = 'lines+markers', name = 'transferidos para Hospitais<br>após agravamento clínico',
                                 visible = 'legendonly'))
        
        fig.add_trace(go.Scatter(x = grafico['dia'], y = grafico['chegando'],
                                 mode = 'lines+markers', name = 'pacientes em processo de<br>transferência para internação<br>no HMCamp',
                                 visible = 'legendonly'))
        
        d = grafico.dia.size
    
        frames = [dict(data = [dict(type = 'scatter', x = grafico.dia[:d+1], y = grafico.comum[:d+1]),
                               dict(type = 'scatter', x = grafico.dia[:d+1], y = grafico.ocupação_comum[:d+1]),
                               dict(type = 'scatter', x = grafico.dia[:d+1], y = grafico.uti[:d+1]),
                               dict(type = 'scatter', x = grafico.dia[:d+1], y = grafico.ocupação_uti[:d+1]),
                               dict(type = 'scatter', x = grafico.dia[:d+1], y = grafico.altas[:d+1]),
                               dict(type = 'scatter', x = grafico.dia[:d+1], y = grafico.óbitos[:d+1]),
                               dict(type = 'scatter', x = grafico.dia[:d+1], y = grafico.transferidos[:d+1]),
                               dict(type = 'scatter', x = grafico.dia[:d+1], y = grafico.chegando[:d+1])],
                       traces = [0, 1, 2, 3, 4, 5, 6, 7],
                      ) for d in range(0, d)]
    
        fig.frames = frames
    
        botoes = [dict(label = 'Animar', method = 'animate',
                       args = [None,dict(frame = dict(duration = 200, redraw = True), fromcurrent = True, mode = 'immediate')])]
    
        fig.update_layout(
            font = dict(family = 'Roboto'),
            title = 'Ocupação dos leitos do HMCamp ' + h + 
                    '<br><i>Fonte: <a href = "https://www.prefeitura.sp.gov.br/cidade/' +
                    'secretarias/saude/vigilancia_em_saude/doencas_e_agravos/coronavirus/' +
                    'index.php?p=295572">Prefeitura de São Paulo</a></i>',
            xaxis_tickangle = 45,
            yaxis_title = 'Número de leitos ou pacientes',
            hovermode = 'x unified',
            hoverlabel = {'namelength' : -1}, #para não truncar o nome de cada trace no hover
            template = 'plotly',
            updatemenus = [dict(type = 'buttons', showactive = False,
                                x = 0.05, y = 0.95,
                                xanchor = 'left', yanchor = 'top',
                                pad = dict(t = 0, r = 10), buttons = botoes)]
        )
    
        # fig.show()
        
        pio.write_html(fig, file = 'docs/graficos/' + h.lower() + '.html',
                       include_plotlyjs = 'directory', auto_open = False, auto_play = False)
        
        #versão mobile
        fig.update_traces(mode = 'lines')
    
        fig.update_xaxes(nticks = 10)
        
        fig.update_layout(
            showlegend = False,
            font = dict(size = 11),
            margin = dict(l = 1, r = 1, b = 1, t = 90, pad = 20)
        )
    
        # fig.show()
        
        pio.write_html(fig, file = 'docs/graficos/' + h.lower() + '-mobile.html',
                       include_plotlyjs = 'directory', auto_open = False, auto_play = False)

def atualiza_service_worker(dados_cidade):
    data_anterior = dados_cidade.data.iat[-2].strftime('%d/%m/%Y')
    data_atual = dados_cidade.data.iat[-1].strftime('%d/%m/%Y')
    
    with open('docs/serviceWorker.js', 'r') as file :
      filedata = file.read()
    
    versao_anterior = int(filedata[16:18])
    
    #primeira atualização no dia
    if(filedata.count(data_atual) == 0):
        versao_atual = 1
        filedata = filedata.replace(data_anterior, data_atual)
    else:
        versao_atual = versao_anterior + 1
        
    print(f'\tCACHE_NAME: Covid19-SP-{data_atual}-{str(versao_atual).zfill(2)}')
        
    versao_anterior = "VERSAO = '" + str(versao_anterior).zfill(2) + "'"
    versao_atual = "VERSAO = '" + str(versao_atual).zfill(2) + "'"
    filedata = filedata.replace(versao_anterior, versao_atual)
    
    with open('docs/serviceWorker.js', 'w') as file:
      file.write(filedata)

if __name__ == '__main__':
    main()