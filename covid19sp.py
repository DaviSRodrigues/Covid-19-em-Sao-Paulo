# -*- coding: utf-8 -*-
"""
Covid-19 em São Paulo

Gera gráficos para acompanhamento da pandemia de Covid-19
na cidade e no estado de São Paulo.

@author: https://github.com/DaviSRodrigues
"""

from datetime import datetime, timedelta
from io import StringIO
import locale
import math
import traceback
import unicodedata

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
    hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total = carrega_dados_cidade()
    dados_munic, dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais, dados_vacinacao, doses_aplicadas, doses_recebidas = carrega_dados_estado()

    print('\nLimpando e enriquecendo dos dados...')
    dados_cidade, dados_munic, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total, dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais, dados_vacinacao = pre_processamento(hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total, dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais, dados_vacinacao, doses_aplicadas, doses_recebidas, dados_munic)
    evolucao_cidade, evolucao_estado = gera_dados_evolucao_pandemia(dados_munic, dados_estado, isolamento, dados_vacinacao)
    evolucao_cidade, evolucao_estado = gera_dados_semana(evolucao_cidade, evolucao_estado, leitos_estaduais, isolamento, internacoes)

    print('\nGerando gráficos e tabelas...')
    gera_graficos(dados_munic, dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total, dados_estado, isolamento, leitos_estaduais, evolucao_cidade, evolucao_estado, internacoes, doencas, dados_raciais, dados_vacinacao)

    print('\nAtualizando serviceWorker.js...')
    atualiza_service_worker(dados_estado)

    print('\nFim')


def carrega_dados_cidade():
    hospitais_campanha = pd.read_csv('dados/hospitais_campanha_sp.csv', sep=',')
    leitos_municipais = pd.read_csv('dados/leitos_municipais.csv', sep=',')
    leitos_municipais_privados = pd.read_csv('dados/leitos_municipais_privados.csv', sep=',')
    leitos_municipais_total = pd.read_csv('dados/leitos_municipais_total.csv', sep=',')

    return hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total


def carrega_dados_estado():
    hoje = data_processamento_estado
    ano = hoje.strftime('%Y')
    mes = hoje.strftime('%m')
    data = hoje.strftime('%Y%m%d')

    try:
        print('\tAtualizando dados dos municípios...')
        URL = 'https://raw.githubusercontent.com/seade-R/dados-covid-sp/master/data/dados_covid_sp.csv'
        dados_munic = pd.read_csv(URL, sep=';', decimal=',')
        opcoes_zip = dict(method='zip', archive_name='dados_munic.csv')
        dados_munic.to_csv('dados/dados_munic.zip', sep=';', decimal=',', index=False, compression=opcoes_zip)
    except Exception as e:
        traceback.print_exception(type(e), e, e.__traceback__)
        print('\tErro ao buscar dados_covid_sp.csv do GitHub: lendo arquivo local.\n')
        dados_munic = pd.read_csv('dados/dados_munic.zip', sep=';', decimal=',')

    try:
        print('\tAtualizando dados estaduais...')
        URL = 'https://raw.githubusercontent.com/seade-R/dados-covid-sp/master/data/sp.csv'
        dados_estado = pd.read_csv(URL, sep=';')
        dados_estado.to_csv('dados/dados_estado_sp.csv', sep=';')
    except Exception as e:
        traceback.print_exception(type(e), e, e.__traceback__)
        print('\tErro ao buscar dados_estado_sp.csv do GitHub: lendo arquivo local.\n')
        dados_estado = pd.read_csv('dados/dados_estado_sp.csv', sep=';', decimal=',', encoding='latin-1', index_col=0)

    try:
        print('\tCarregando dados de isolamento social...')
        isolamento = pd.read_csv('dados/isolamento_social.csv', sep=',')
    except Exception as e:
        print(f'\tErro ao buscar isolamento_social.csv\n\t{e}')

    try:
        print('\tAtualizando dados de internações...')
        URL = ('https://raw.githubusercontent.com/seade-R/dados-covid-sp/master/data/plano_sp_leitos_internacoes.csv')
        internacoes = pd.read_csv(URL, sep=';', decimal=',', thousands='.')
        internacoes.to_csv('dados/internacoes.csv', sep=';', decimal=',')
    except Exception as e:
        try:
            print(f'\tErro ao buscar internacoes.csv do GitHub: lendo arquivo da Seade.\n\t{e}')
            URL = (f'http://www.seade.gov.br/wp-content/uploads/{ano}/{mes}/Leitos-e-Internacoes.csv')
            internacoes = pd.read_csv(URL, sep=';', encoding='latin-1', decimal=',', thousands='.', engine='python',
                                      skipfooter=2)
        except Exception as e:
            print(f'\tErro ao buscar internacoes.csv da Seade: lendo arquivo local.\n\t{e}')
            internacoes = pd.read_csv('dados/internacoes.csv', sep=';', decimal=',', thousands='.', index_col=0)

    try:
        print('\tAtualizando dados de doenças preexistentes...')
        URL = ('https://raw.githubusercontent.com/seade-R/dados-covid-sp/master/data/casos_obitos_doencas_preexistentes.csv.zip')
        doencas = pd.read_csv(URL, sep=';')
        opcoes_zip = dict(method='zip', archive_name='doencas_preexistentes.csv')
        doencas.to_csv('dados/doencas_preexistentes.zip', sep=';', compression=opcoes_zip)
    except Exception as e:
        try:
            print(f'\tErro ao buscar doencas_preexistentes.csv do GitHub: lendo arquivo local.\n\t{e}')
            doencas = pd.read_csv('dados/doencas_preexistentes.zip', sep=';', index_col=0)
        except Exception as e:
            print(f'\tErro ao buscar doencas_preexistentes.csv localmente: lendo arquivo da Seade.\n\t{e}')
            URL = f'http://www.seade.gov.br/wp-content/uploads/{ano}/{mes}/casos_obitos_doencas_preexistentes.csv'
            doencas = pd.read_csv(URL, sep=';', encoding='latin-1')

    try:
        print('\tAtualizando dados de casos/óbitos por raça e cor...')
        URL = ('https://raw.githubusercontent.com/seade-R/dados-covid-sp/master/data/casos_obitos_raca_cor.csv.zip')
        dados_raciais = pd.read_csv(URL, sep=';')
        opcoes_zip = dict(method='zip', archive_name='dados_raciais.csv')
        dados_raciais.to_csv('dados/dados_raciais.zip', sep=';', compression=opcoes_zip)
    except Exception as e:
        print(f'\tErro ao buscar dados_raciais.csv do GitHub: lendo arquivo local.\n\t{e}')
        dados_raciais = pd.read_csv('dados/dados_raciais.zip', sep=';', index_col=0)

    print('\tAtualizando dados da campanha de vacinação...')

    headers = {'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/88.0.4324.182 '
                             'Safari/537.36 '
                             'Edg/88.0.705.74'}

    try:
        print('\t\tDoses aplicadas por município...')
        URL = f'https://www.saopaulo.sp.gov.br/wp-content/uploads/{ano}/{mes}/{data}_vacinometro.csv'
        req = requests.get(URL, headers=headers, stream=True)
        req.encoding = req.apparent_encoding
        doses_aplicadas = pd.read_csv(StringIO(req.text), sep=';', encoding='utf-8-sig')
        doses_aplicadas.columns = ['municipio', 'dose', 'contagem']
    except Exception as e:
        print(f'\t\tErro ao buscar {data}_vacinometro.csv da Seade: {e}')
        doses_aplicadas = None

    try:
        print('\t\tDoses recebidas por cada município...')
        URL = f'https://www.saopaulo.sp.gov.br/wp-content/uploads/{ano}/{mes}/{data}_painel_distribuicao_doses.csv'
        req = requests.get(URL, headers=headers, stream=True)
        req.encoding = req.apparent_encoding
        doses_recebidas = pd.read_csv(StringIO(req.text), sep=';', encoding='utf-8-sig')
        doses_recebidas.columns = ['municipio', 'contagem']
    except Exception as e:
        print(f'\t\tErro ao buscar {data}_painel_distribuicao_doses.csv da Seade: {e}')
        doses_recebidas = None

    leitos_estaduais = pd.read_csv('dados/leitos_estaduais.csv', index_col=0)
    dados_vacinacao = pd.read_csv('dados/dados_vacinacao.zip')

    return dados_munic, dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais, dados_vacinacao, doses_aplicadas, doses_recebidas


def pre_processamento(hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total, dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais, dados_vacinacao, doses_aplicadas, doses_recebidas, dados_munic):
    print('\tDados municipais...')
    dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total = pre_processamento_cidade(dados_munic, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total)
    print('\tDados estaduais...')
    dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais, dados_vacinacao, dados_munic = pre_processamento_estado(dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais, dados_vacinacao, doses_aplicadas, doses_recebidas, dados_munic)

    return dados_cidade, dados_munic, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total, dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais, dados_vacinacao


def pre_processamento_cidade(dados_munic, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total):
    dados_cidade = dados_munic.loc[dados_munic.nome_munic == 'São Paulo', ['datahora', 'casos', 'casos_novos', 'obitos', 'obitos_novos', 'letalidade']]
    dados_cidade.columns = ['data', 'confirmados', 'casos_dia', 'óbitos', 'óbitos_dia', 'letalidade']
    dados_cidade['letalidade'] = dados_cidade.letalidade * 100
    dados_cidade['data'] = pd.to_datetime(dados_cidade.data)
    dados_cidade['dia'] = dados_cidade.data.apply(lambda d: d.strftime('%d %b %y'))

    hospitais_campanha['data'] = pd.to_datetime(hospitais_campanha.data, format='%d/%m/%Y')
    hospitais_campanha['dia'] = hospitais_campanha.data.apply(lambda d: d.strftime('%d %b %y'))

    leitos_municipais['data'] = pd.to_datetime(leitos_municipais.data, format='%d/%m/%Y')
    leitos_municipais['dia'] = leitos_municipais.data.apply(lambda d: d.strftime('%d %b %y'))

    leitos_municipais_privados['data'] = pd.to_datetime(leitos_municipais_privados.data, format='%d/%m/%Y')
    leitos_municipais_privados['dia'] = leitos_municipais_privados.data.apply(lambda d: d.strftime('%d %b %y'))

    leitos_municipais_total['data'] = pd.to_datetime(leitos_municipais_total.data, format='%d/%m/%Y')
    leitos_municipais_total['dia'] = leitos_municipais_total.data.apply(lambda d: d.strftime('%d %b %y'))

    return dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total


def formata_municipio(m):
    return m.title() \
        .replace(' Da ', ' da ') \
        .replace(' De ', ' de ') \
        .replace(' Do ', ' do ') \
        .replace(' Das ', ' das ') \
        .replace(' Dos ', ' dos ')


def pre_processamento_estado(dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais, dados_vacinacao, doses_aplicadas, doses_recebidas, dados_munic):
    dados_estado.columns = ['data', 'total_casos', 'total_obitos']
    dados_estado['data'] = pd.to_datetime(dados_estado.data)
    dados_estado['dia'] = dados_estado.data.apply(lambda d: d.strftime('%d %b %y'))

    dados_munic['datahora'] = pd.to_datetime(dados_munic.datahora)

    isolamento_atualizado = None
    tentativas = 0

    def busca_isolamento():
        try:
            nonlocal tentativas, isolamento_atualizado
            tentativas = tentativas + 1
            print(f'\t\t{f"Tentativa {tentativas}: " if tentativas > 1 else ""}'
                  f'Atualizando dados de isolamento social...')
            URL = 'https://public.tableau.com/views/IsolamentoSocial/DADOS.csv?:showVizHome=no'
            isolamento_atualizado = pd.read_csv(URL, sep=',')
        except Exception:
            if tentativas <= 3:
                busca_isolamento()
            else:
                print('\t\tErro: não foi possível obter os dados atualizados de isolamento social.')

    busca_isolamento()

    if isolamento_atualizado is not None:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        ontem = data_processamento_estado - timedelta(days=1)
        ontem_str = ontem.strftime('%A, %d/%m')

        isolamento_atualizado.columns = ['codigo_ibge', 'data', 'município', 'populacao', 'UF', 'isolamento']
        isolamento_atualizado.drop(columns='codigo_ibge', inplace=True)
        isolamento_atualizado = isolamento_atualizado.loc[isolamento_atualizado.data == ontem_str]

        data_arquivo = pd.to_datetime(isolamento.iloc[-1]['data'])
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

        if data_arquivo.date() < ontem.date() and not isolamento_atualizado.empty:
            isolamento_atualizado['isolamento'] = pd.to_numeric(isolamento_atualizado.isolamento.str.replace('%', ''))
            isolamento_atualizado['município'] = isolamento_atualizado.município.apply(lambda m: formata_municipio(m))
            isolamento_atualizado['data'] = isolamento_atualizado.data.apply(
                lambda d: datetime.strptime(d.split(', ')[1] + '/' + str(ontem.year), '%d/%m/%Y'))
            isolamento_atualizado['dia'] = isolamento_atualizado.data.apply(lambda d: d.strftime('%d %b %y'))

            isolamento = isolamento.append(isolamento_atualizado)
            isolamento['data'] = pd.to_datetime(isolamento.data)
            isolamento.sort_values(by=['data', 'isolamento'], inplace=True)
            isolamento.to_csv('dados/isolamento_social.csv', sep=',', index=False)

    isolamento['data'] = pd.to_datetime(isolamento.data)

    leitos_estaduais['data'] = pd.to_datetime(leitos_estaduais.data, format='%d/%m/%Y')

    internacoes.columns = ['data', 'drs', 'pacientes_uti_mm7d', 'total_covid_uti_mm7d', 'ocupacao_leitos',
                           'pop', 'leitos_pc', 'internacoes_7d', 'internacoes_7d_l', 'internacoes_7v7',
                           'pacientes_uti_ultimo_dia', 'total_covid_uti_ultimo_dia', 'ocupacao_leitos_ultimo_dia']
    internacoes['data'] = pd.to_datetime(internacoes.data)
    internacoes['dia'] = internacoes.data.apply(lambda d: d.strftime('%d %b %y'))

    if internacoes.data.max() > leitos_estaduais.data.max():
        novos_dados = {'data': internacoes.data.max(),
                       'sp_uti': None,
                       'sp_enfermaria': None,
                       'rmsp_uti': None,
                       'rmsp_enfermaria': None}

        leitos_estaduais = leitos_estaduais.append(novos_dados, ignore_index=True)

    def atualizaOcupacaoUTI(series):
        ocupacao = internacoes.loc[(internacoes.drs == 'Estado de São Paulo') & (internacoes.data == series['data']), 'ocupacao_leitos_ultimo_dia']
        series['sp_uti'] = ocupacao.item() if any(ocupacao) else series['sp_uti']

        filtro_drs = ((internacoes.drs.str.contains('SP')) | (internacoes.drs == 'Município de São Paulo'))
        leitos = internacoes.loc[(filtro_drs) & (internacoes.data == series['data']), 'total_covid_uti_ultimo_dia'].sum()

        if leitos > 0:
            pacientes = internacoes.loc[(filtro_drs) & (internacoes.data == series['data']), 'pacientes_uti_ultimo_dia'].sum()
            ocupacao = pacientes / leitos
            series['rmsp_uti'] = round(ocupacao * 100, 2)

        return series

    leitos_estaduais = leitos_estaduais.apply(lambda linha: atualizaOcupacaoUTI(linha), axis=1)

    leitos_estaduais['dia'] = leitos_estaduais.data.apply(lambda d: d.strftime('%d %b %y'))
    leitos_estaduais['data'] = leitos_estaduais.data.apply(lambda d: d.strftime('%d/%m/%Y'))
    colunas = ['data', 'sp_uti', 'sp_enfermaria', 'rmsp_uti', 'rmsp_enfermaria']
    leitos_estaduais[colunas].to_csv('dados/leitos_estaduais.csv', sep=',')
    leitos_estaduais['data'] = pd.to_datetime(leitos_estaduais.data, format='%d/%m/%Y')

    doencas.columns = ['municipio', 'codigo_ibge', 'idade', 'sexo', 'covid19', 'data_inicio_sintomas', 'obito', 'asma',
                       'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica', 'doenca_neurologica',
                       'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera',
                       'sindrome_de_down']

    doencas = doencas.groupby(
        ['obito', 'covid19', 'idade', 'sexo', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica',
         'doenca_hepatica', 'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros',
         'pneumopatia', 'puerpera', 'sindrome_de_down']) \
        .agg({'asma': 'count', 'cardiopatia': 'count', 'diabetes': 'count', 'doenca_hematologica': 'count',
              'doenca_hepatica': 'count', 'doenca_neurologica': 'count', 'doenca_renal': 'count',
              'imunodepressao': 'count', 'obesidade': 'count', 'outros': 'count', 'pneumopatia': 'count',
              'puerpera': 'count', 'sindrome_de_down': 'count'})

    def calcula_letalidade(series):
        # localiza a linha atual passada como parâmetro e obtém a o índice da linha anterior
        indice = dados_estado.index[dados_estado.data == series['data']].item() - 1

        if indice >= 0:
            series['casos_dia'] = series['total_casos'] - dados_estado.loc[indice, 'total_casos']
            series['obitos_dia'] = series['total_obitos'] - dados_estado.loc[indice, 'total_obitos']
        else:
            series['casos_dia'] = series['total_casos']
            series['obitos_dia'] = series['total_obitos']

        # calcula a taxa de letalidade até a data atual
        if series['total_casos'] > 0:
            series['letalidade'] = round((series['total_obitos'] / series['total_casos']) * 100, 2)

        return series

    dados_estado = dados_estado.apply(lambda linha: calcula_letalidade(linha), axis=1)

    dados_raciais = dados_raciais[['obito', 'raca_cor']]
    dados_raciais = dados_raciais.fillna('IGNORADO')
    dados_raciais.loc[dados_raciais.raca_cor == 'NONE', 'raca_cor'] = 'IGNORADO'
    dados_raciais['raca_cor'] = dados_raciais.raca_cor.str.title()
    dados_raciais = dados_raciais.groupby(['obito', 'raca_cor']).agg(contagem=('obito', 'count'))

    def atualiza_doses(municipio):
        temp = doses_aplicadas.loc[doses_aplicadas['municipio'] == municipio]

        doses = temp.loc[temp.dose == '1° Dose', 'contagem']
        primeira_dose = int(doses.iat[0]) if not doses.empty else None

        doses = temp.loc[temp.dose == '2° Dose', 'contagem']
        segunda_dose = int(doses.iat[0]) if not doses.empty else None

        if doses_recebidas is not None:
            recebidas = doses_recebidas.loc[doses_recebidas.municipio == municipio, 'contagem']
            recebidas = None if recebidas.empty else recebidas.iat[0]
        else:
            recebidas = None

        novos_dados = {'data': hoje.date(),
                       'municipio': municipio,
                       'doses_recebidas': recebidas,
                       '1a_dose': primeira_dose,
                       '2a_dose': segunda_dose}

        nonlocal dados_vacinacao
        dados_vacinacao = dados_vacinacao.append(novos_dados, ignore_index=True)

    def atualiza_populacao():
        hoje_str = hoje.strftime('%Y-%m-%d')
        dados_pop = dados_munic.loc[dados_munic.datahora == hoje_str, ['nome_munic', 'datahora', 'pop']]
        dados_pop['nome_munic'] = dados_pop.nome_munic.apply(
            lambda m: ''.join(c for c in unicodedata.normalize('NFD', m.upper()) if unicodedata.category(c) != 'Mn'))

        nonlocal dados_vacinacao
        dados_vacinacao['populacao'] = None

        for m in list(dados_vacinacao['municipio'].unique()):
            pop = dados_pop.loc[dados_pop.nome_munic == m, 'pop']
            pop = None if pop.empty else pop.iat[0]

            dados_vacinacao.loc[dados_vacinacao.municipio == m, 'populacao'] = pop

        pop_estado = internacoes.loc[(internacoes.drs == 'Estado de São Paulo') &
                                     (internacoes.data == internacoes.data.max()), 'pop'].iat[0]

        dados_vacinacao.loc[dados_vacinacao.municipio == 'ESTADO DE SAO PAULO', 'populacao'] = pop_estado

    def atualiza_estado():
        nonlocal dados_vacinacao
        filtro_e = dados_vacinacao.municipio != 'ESTADO DE SAO PAULO'
        data_atual = pd.to_datetime(hoje.strftime('%Y-%m-%d'))  # para tirar as horas
        filtro_d = dados_vacinacao.data == data_atual

        novos_dados = {'data': data_atual,
                       'municipio': 'ESTADO DE SAO PAULO',
                       'doses_recebidas': dados_vacinacao.loc[filtro_d & filtro_e, 'doses_recebidas'].sum(),
                       '1a_dose': dados_vacinacao.loc[filtro_d & filtro_e, '1a_dose'].sum(),
                       '2a_dose': dados_vacinacao.loc[filtro_d & filtro_e, '2a_dose'].sum(),
                       'populacao': internacoes.loc[(internacoes.drs == 'Estado de São Paulo') & (internacoes.data == internacoes.data.max()), 'pop'].iat[0]}

        dados_vacinacao = dados_vacinacao.append(novos_dados, ignore_index=True)

    def calcula_campos_adicionais(linha):
        if linha['data'] != hoje.date():
            return linha

        primeira_dose = 0 if linha['1a_dose'] is None or math.isnan(linha['1a_dose']) else linha['1a_dose']
        segunda_dose = 0 if linha['2a_dose'] is None or math.isnan(linha['2a_dose']) else linha['2a_dose']
        populacao = 0 if linha['populacao'] is None or math.isnan(linha['populacao']) else linha['populacao']
        doses_recebidas = 0 if linha['doses_recebidas'] is None or math.isnan(linha['doses_recebidas']) else linha['doses_recebidas']

        linha['total_doses'] = primeira_dose + segunda_dose

        try:
            linha['perc_vacinadas_1a_dose'] = (primeira_dose / populacao) * 100
        except ZeroDivisionError:
            linha['perc_vacinadas_1a_dose'] = None

        try:
            linha['perc_vacinadas_2a_dose'] = (segunda_dose / populacao) * 100
        except ZeroDivisionError:
            linha['perc_vacinadas_2a_dose'] = None

        try:
            if doses_recebidas == 0:
                indice = pd.Series(dtype='float64')
                recebidas_anterior = hoje - timedelta(days=1)

                while indice.empty and recebidas_anterior.date() >= dados_vacinacao.data.min().date():
                    indice = dados_vacinacao.index[(dados_vacinacao.data == recebidas_anterior.date()) &
                                                   (dados_vacinacao.municipio == linha['doses_recebidas'])]
                    recebidas_anterior = recebidas_anterior - timedelta(days=1)

                if not indice.empty:
                    indice = indice.item()
                    doses_recebidas = dados_vacinacao.loc[indice, 'doses_recebidas']

            linha['perc_aplicadas'] = (linha['total_doses'] / doses_recebidas) * 100
        except ZeroDivisionError:
            linha['perc_aplicadas'] = None

        # obtém o dia anterior
        indice = pd.Series(dtype='float64')
        dia_anterior = hoje - timedelta(days=1)

        while indice.empty and dia_anterior.date() >= dados_vacinacao.data.min().date():
            indice = dados_vacinacao.index[(dados_vacinacao.data == dia_anterior.date()) &
                                           (dados_vacinacao.municipio == linha['municipio'])]
            dia_anterior = dia_anterior - timedelta(days=1)

        if indice.empty:
            linha['aplicadas_dia'] = linha['total_doses']
        else:
            indice = indice.item()
            linha['aplicadas_dia'] = linha['total_doses'] - dados_vacinacao.loc[indice, 'total_doses']

        return linha

    dados_vacinacao['data'] = pd.to_datetime(dados_vacinacao.data, format='%d/%m/%Y')
    hoje = data_processamento_estado

    if dados_vacinacao.data.max().date() < hoje.date() and doses_aplicadas is not None:
        dados_vacinacao['municipio'] = dados_vacinacao.municipio.apply(
            lambda m: ''.join(c for c in unicodedata.normalize('NFD', m.upper()) if unicodedata.category(c) != 'Mn'))

        doses_aplicadas['municipio'] = doses_aplicadas.municipio.apply(
            lambda m: ''.join(c for c in unicodedata.normalize('NFD', m.upper()) if unicodedata.category(c) != 'Mn'))

        if doses_recebidas is not None:
            doses_recebidas['municipio'] = doses_recebidas.municipio.apply(
                lambda m: ''.join(c for c in unicodedata.normalize('NFD', m.upper()) if unicodedata.category(c) != 'Mn'))

        for m in list(doses_aplicadas.municipio.unique()):
            atualiza_doses(m)

        atualiza_populacao()
        atualiza_estado()
        dados_vacinacao = dados_vacinacao.apply(lambda linha: calcula_campos_adicionais(linha), axis=1)

        dados_vacinacao.sort_values(by=['data', 'municipio'], ascending=True, inplace=True)
        dados_vacinacao['data'] = dados_vacinacao.data.apply(lambda d: d.strftime('%d/%m/%Y'))
        opcoes_zip = dict(method='zip', archive_name='dados_vacinacao.csv')
        dados_vacinacao.to_csv('dados/dados_vacinacao.zip', index=False, compression=opcoes_zip)
        dados_vacinacao['data'] = pd.to_datetime(dados_vacinacao.data, format='%d/%m/%Y')

    return dados_estado, isolamento, leitos_estaduais, internacoes, doencas, dados_raciais, dados_vacinacao, dados_munic


def _converte_semana(data):
    convertion = data.strftime('%Y-W%U')

    if 'W00' in convertion:
        last_year = int(convertion.split('-')[0]) - 1
        convertion = pd.to_datetime('12-31-' + str(last_year)).strftime('%Y-W%U')

    return convertion


def _formata_semana_extenso(data, inclui_ano=True):
    # http://portalsinan.saude.gov.br/calendario-epidemiologico-2020
    if inclui_ano:
        return datetime.strptime(data + '-0', '%Y-W%U-%w').strftime('%d/%b/%y') + ' a ' + \
               datetime.strptime(data + '-6', '%Y-W%U-%w').strftime('%d/%b/%y')
    else:
        return datetime.strptime(data + '-0', '%Y-W%U-%w').strftime('%d/%b') + ' a ' + \
               datetime.strptime(data + '-6', '%Y-W%U-%w').strftime('%d/%b')

def gera_dados_evolucao_pandemia(dados_munic, dados_estado, isolamento, dados_vacinacao):
    print('\tProcessando dados da evolução da pandemia...')
    # criar dataframe relação: comparar média de isolamento social de duas
    # semanas atrás com a quantidade de casos e de óbitos da semana atual
    isolamento['data_futuro'] = isolamento.data.apply(lambda d: d + timedelta(weeks=2))

    filtro = isolamento.município == 'Estado de São Paulo'
    colunas = ['data_futuro', 'isolamento']
    esquerda = isolamento.loc[filtro, colunas].groupby(['data_futuro']).mean().reset_index()
    esquerda.columns = ['data', 'isolamento']

    estado = dados_estado[['data', 'obitos_dia', 'casos_dia']].groupby(['data']).sum().reset_index()
    estado.columns = ['data', 'obitos_semana', 'casos_semana']

    estado = esquerda.merge(estado, on=['data'], how='outer', suffixes=('_isolamento', '_estado'))

    filtro = dados_vacinacao.municipio == 'ESTADO DE SAO PAULO'
    colunas = ['data', 'aplicadas_dia', 'perc_vacinadas_1a_dose']
    vacinacao = dados_vacinacao.loc[filtro, colunas].groupby(['data']).sum().reset_index()
    vacinacao.columns = ['data', 'vacinadas_semana', 'perc_vac_semana']

    estado = vacinacao.merge(estado, on=['data'], how='outer', suffixes=('_vacinacao', '_estado'))

    estado['data'] = estado.data.apply(lambda d: _converte_semana(d))

    estado = estado.groupby('data') \
                   .agg({'isolamento': 'mean', 'obitos_semana': sum, 'casos_semana': sum,
                         'vacinadas_semana': sum, 'perc_vac_semana': max}) \
                   .reset_index()

    estado['data'] = estado.data.apply(lambda d: _formata_semana_extenso(d))

    estado['casos_semana'] = estado.casos_semana.apply(lambda c: math.nan if c == 0 else c)
    estado['obitos_semana'] = estado.obitos_semana.apply(lambda c: math.nan if c == 0 else c)
    estado['vacinadas_semana'] = estado.vacinadas_semana.apply(lambda c: math.nan if c == 0 else c)

    evolucao_estado = estado

    # dados municipais
    filtro = isolamento.município == 'São Paulo'
    colunas = ['data_futuro', 'isolamento']
    esquerda = isolamento.loc[filtro, colunas].groupby(['data_futuro']).mean().reset_index()
    esquerda.columns = ['data', 'isolamento']

    # cidade = dados_cidade[['data', 'óbitos_dia', 'casos_dia']].groupby(['data']).sum().reset_index()
    cidade = dados_munic.loc[dados_munic.nome_munic == 'São Paulo', ['datahora', 'obitos_novos', 'casos_novos']].groupby(['datahora']).sum().reset_index()
    cidade.columns = ['data', 'obitos_semana', 'casos_semana']

    cidade = esquerda.merge(cidade, on=['data'], how='outer', suffixes=('_isolamento', '_cidade'))

    filtro = dados_vacinacao.municipio == 'SAO PAULO'
    colunas = ['data', 'aplicadas_dia', 'perc_vacinadas_1a_dose']
    vacinacao = dados_vacinacao.loc[filtro, colunas].groupby(['data']).sum().reset_index()
    vacinacao.columns = ['data', 'vacinadas_semana', 'perc_vac_semana']

    cidade = vacinacao.merge(cidade, on=['data'], how='outer', suffixes=('_vacinacao', '_cidade'))

    cidade['data'] = cidade.data.apply(lambda d: _converte_semana(d))

    cidade = cidade.groupby('data') \
                   .agg({'isolamento': 'mean', 'obitos_semana': sum, 'casos_semana': sum,
                         'vacinadas_semana': sum, 'perc_vac_semana': max}) \
                   .reset_index()

    cidade['data'] = cidade.data.apply(lambda d: _formata_semana_extenso(d))

    cidade['casos_semana'] = cidade.casos_semana.apply(lambda c: math.nan if c == 0 else c)
    cidade['obitos_semana'] = cidade.obitos_semana.apply(lambda c: math.nan if c == 0 else c)
    cidade['vacinadas_semana'] = cidade.vacinadas_semana.apply(lambda c: math.nan if c == 0 else c)

    evolucao_cidade = cidade

    return evolucao_cidade, evolucao_estado


def gera_dados_semana(evolucao_cidade, evolucao_estado, leitos_estaduais, isolamento, internacoes):
    print('\tProcessando dados semanais...')

    def calcula_variacao(dados, linha):
        indice = dados.index[dados.data == linha['data']].item() - 1

        if indice >= 0:
            casos_anterior = dados.loc[indice, 'casos_semana']
            obitos_anterior = dados.loc[indice, 'obitos_semana']
            uti_anterior = dados.loc[indice, 'uti']
            isolamento_anterior = dados.loc[indice, 'isolamento_atual']
            isolamento_2sem_anterior = dados.loc[indice, 'isolamento']
            vacinadas_anterior = dados.loc[indice, 'vacinadas_semana']
            perc_vac_semana_anterior = dados.loc[indice, 'perc_vac_semana']

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

            if vacinadas_anterior > 0:
                linha['variacao_vacinadas'] = ((linha['vacinadas_semana'] / vacinadas_anterior) - 1) * 100

            if perc_vac_semana_anterior > 0:
                linha['variacao_perc_vac'] = ((linha['perc_vac_semana'] / perc_vac_semana_anterior) - 1) * 100

        return linha

    # cálculo da média da taxa de ocupação de leitos de UTI na semana
    leitos = pd.DataFrame()
    leitos['data'] = internacoes.loc[internacoes.drs == 'Município de São Paulo', 'data'].apply(lambda d: _formata_semana_extenso(_converte_semana(d)))
    leitos['uti'] = internacoes.loc[internacoes.drs == 'Município de São Paulo', 'ocupacao_leitos_ultimo_dia']

    leitos = leitos.groupby('data').mean().reset_index()

    evolucao_cidade = evolucao_cidade.merge(leitos, on='data', how='outer', suffixes=('_efeito', '_leitos'))

    filtro = isolamento.município == 'São Paulo'
    colunas = ['data', 'isolamento']

    isola_atual = isolamento.loc[filtro, colunas]
    isola_atual['data'] = isola_atual.data.apply(lambda d: _formata_semana_extenso(_converte_semana(d)))
    isola_atual = isola_atual.groupby('data').mean().reset_index()
    isola_atual.columns = ['data', 'isolamento_atual']

    evolucao_cidade = evolucao_cidade.merge(isola_atual, on='data', how='left', suffixes=('_efeito', '_isola'))

    evolucao_cidade = evolucao_cidade.apply(lambda linha: calcula_variacao(evolucao_cidade, linha), axis=1)

    def obter_internacoes(local, linha):
        df = internacoes.loc[:, ['data', 'drs', 'internacoes_7d', 'internacoes_7v7']]
        df['data'] = df.data.apply(lambda d: _formata_semana_extenso(_converte_semana(d)))

        df = df[(df.data == linha.data) & (df.drs == local)]

        if df.empty:
            return linha

        linha['internacoes'] = df.tail(1).internacoes_7d.item()
        linha['variacao_internacoes'] = df.tail(1).internacoes_7v7.item()

        return linha

    evolucao_cidade = evolucao_cidade.apply(lambda linha: obter_internacoes('Município de São Paulo', linha), axis=1)

    # dados estaduais
    leitos = pd.DataFrame()
    leitos['data'] = leitos_estaduais.data.apply(lambda d: _formata_semana_extenso(_converte_semana(d)))
    leitos['uti'] = leitos_estaduais.sp_uti

    leitos = leitos.groupby('data').mean().reset_index()

    evolucao_estado = evolucao_estado.merge(leitos, on='data', how='outer', suffixes=('_efeito', '_leitos'))

    filtro = isolamento.município == 'Estado de São Paulo'
    colunas = ['data', 'isolamento']

    isola_atual = isolamento.loc[filtro, colunas]
    isola_atual['data'] = isola_atual.data.apply(lambda d: _formata_semana_extenso(_converte_semana(d)))
    isola_atual = isola_atual.groupby('data').mean().reset_index()
    isola_atual.columns = ['data', 'isolamento_atual']

    evolucao_estado = evolucao_estado.merge(isola_atual, on='data', how='left', suffixes=('_efeito', '_isola'))

    evolucao_estado = evolucao_estado.apply(lambda linha: calcula_variacao(evolucao_estado, linha), axis=1)

    evolucao_estado = evolucao_estado.apply(lambda linha: obter_internacoes('Estado de São Paulo', linha), axis=1)

    return evolucao_cidade, evolucao_estado


def gera_graficos(dados_munic, dados_cidade, hospitais_campanha, leitos_municipais, leitos_municipais_privados, leitos_municipais_total, dados_estado, isolamento, leitos_estaduais, evolucao_cidade, evolucao_estado, internacoes, doencas, dados_raciais, dados_vacinacao):
    print('\tResumo da campanha de vacinação...')
    gera_resumo_vacinacao(dados_vacinacao)
    print('\tResumo diário...')
    gera_resumo_diario(dados_munic, dados_cidade, leitos_municipais_total, dados_estado, leitos_estaduais, isolamento, internacoes, dados_vacinacao)
    print('\tResumo semanal...')
    gera_resumo_semanal(evolucao_cidade, evolucao_estado)
    print('\tEvolução da pandemia no estado...')
    gera_evolucao_estado(evolucao_estado)
    print('\tEvolução da pandemia na cidade...')
    gera_evolucao_cidade(evolucao_cidade)
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
    print('\tLeitos no estado...')
    gera_leitos_estaduais(leitos_estaduais)
    print('\tDepartamentos Regionais de Saúde...')
    gera_drs(internacoes)
    print('\tEvolução da campanha de vacinação no estado...')
    gera_evolucao_vacinacao_estado(dados_vacinacao)
    print('\tEvolução da campanha de vacinação na cidade...')
    gera_evolucao_vacinacao_cidade(dados_vacinacao)
    print('\tPopulação vacinada...')
    gera_populacao_vacinada(dados_vacinacao)
    print('\t1ª dose x 2ª dose...')
    gera_tipo_doses(dados_vacinacao)
    print('\tDoses recebidas x aplicadas...')
    gera_doses_aplicadas(dados_vacinacao)
    print('\tTabela da campanha de vacinação...')
    gera_tabela_vacinacao(dados_vacinacao)
    # print('\tHospitais de campanha...')
    # gera_hospitais_campanha(hospitais_campanha)


def gera_resumo_vacinacao(dados_vacinacao):
    filtro_data = dados_vacinacao.data.dt.date == data_processamento_estado.date()
    filtro_estado = dados_vacinacao.municipio == 'ESTADO DE SAO PAULO'
    filtro_cidade = dados_vacinacao.municipio == 'SAO PAULO'

    cabecalho = ['<b>Campanha de<br>vacinação</b>',
                 '<b>Estado de SP</b><br><i>' + data_processamento_estado.strftime('%d/%m/%Y') + '</i>',
                 '<b>Cidade de SP</b><br><i>' + data_processamento_estado.strftime('%d/%m/%Y') + '</i>']

    info = ['<b>Doses aplicadas</b>', '<b>1ª dose</b>', '<b>2ª dose</b>', '<b>População vacinada (%)</b>']

    doses_aplicadas = dados_vacinacao.loc[filtro_data & filtro_estado, 'total_doses']
    doses_aplicadas = 'indisponível' if doses_aplicadas.empty else f'{doses_aplicadas.item():7,.0f}'.replace(',', '.')

    dose_1 = dados_vacinacao.loc[filtro_data & filtro_estado, '1a_dose']
    dose_1 = 'indisponível' if dose_1.empty else f'{dose_1.item():7,.0f}'.replace(',', '.')

    dose_2 = dados_vacinacao.loc[filtro_data & filtro_estado, '2a_dose']
    dose_2 = 'indisponível' if dose_2.empty else f'{dose_2.item():7,.0f}'.replace(',', '.')

    pop_vacinada = dados_vacinacao.loc[filtro_data & filtro_estado, 'perc_vacinadas_1a_dose']
    pop_vacinada = 'indisponível' if pop_vacinada.empty else f'{pop_vacinada.item():7.2f}%'.replace('.', ',')

    estado = [doses_aplicadas,
              dose_1,
              dose_2,
              pop_vacinada]

    doses_aplicadas = dados_vacinacao.loc[filtro_data & filtro_cidade, 'total_doses']
    doses_aplicadas = 'indisponível' if doses_aplicadas.empty else f'{doses_aplicadas.item():7,.0f}'.replace(',', '.')

    dose_1 = dados_vacinacao.loc[filtro_data & filtro_cidade, '1a_dose']
    dose_1 = 'indisponível' if dose_1.empty else f'{dose_1.item():7,.0f}'.replace(',', '.')

    dose_2 = dados_vacinacao.loc[filtro_data & filtro_cidade, '2a_dose']
    dose_2 = 'indisponível' if dose_2.empty else f'{dose_2.item():7,.0f}'.replace(',', '.')

    pop_vacinada = dados_vacinacao.loc[filtro_data & filtro_cidade, 'perc_vacinadas_1a_dose']
    pop_vacinada = 'indisponível' if pop_vacinada.empty else f'{pop_vacinada.item():7.2f}%'.replace('.', ',')

    cidade = [doses_aplicadas,
              dose_1,
              dose_2,
              pop_vacinada]

    fig = go.Figure(data=[go.Table(header=dict(values=cabecalho,
                                               fill_color='#00aabb',
                                               font=dict(color='white'),
                                               align=['right', 'right', 'right'],
                                               line=dict(width=5)),
                                   cells=dict(values=[info, estado, cidade],
                                              fill_color='lavender',
                                              align='right',
                                              line=dict(width=5)),
                                   columnwidth=[1, 1, 1])])

    fig.update_layout(
        font=dict(size=15, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=30, pad=5),
        annotations=[dict(x=0, y=0, showarrow=False, font=dict(size=13),
                          text='<i><b>Fonte:</b> <a href = "https://www.seade.gov.br/coronavirus/">'
                               'Governo do Estado de São Paulo</a></i>')],
        height=240
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/resumo-vacinacao.html', include_plotlyjs='directory', auto_open=False)

    fig.update_layout(
        font=dict(size=13, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=30, pad=5),
        annotations=[dict(x=0, y=0)],
        height=260
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/resumo-vacinacao-mobile.html', include_plotlyjs='directory', auto_open=False)


def gera_resumo_diario(dados_munic, dados_cidade, leitos_municipais, dados_estado, leitos_estaduais, isolamento, internacoes, dados_vacinacao):
    hoje = data_processamento_estado

    cabecalho = ['<b>Resumo diário</b>',
                 '<b>Estado de SP</b><br><i>' + hoje.strftime('%d/%m/%Y') + '</i>',
                 '<b>Cidade de SP</b><br><i>' + hoje.strftime('%d/%m/%Y') + '</i>']

    info = ['<b>Vacinadas</b>', '<b>Casos</b>', '<b>Casos no dia</b>', '<b>Óbitos</b>', '<b>Óbitos no dia</b>',
            '<b>Letalidade</b>', '<b>Leitos Covid-19</b>', '<b>Ocupação de UTIs</b>', '<b>Isolamento</b>']

    filtro = (isolamento.município == 'Estado de São Paulo') & (isolamento.data.dt.date == hoje.date() - timedelta(days=1))
    isolamento_atual = isolamento.loc[filtro, 'isolamento']
    isolamento_atual = 'indisponível' if isolamento_atual.empty else f'{isolamento_atual.item():7.0f}%'.replace('.', ',')

    filtro = (dados_vacinacao.municipio == 'ESTADO DE SAO PAULO') & (dados_vacinacao.data.dt.date == hoje.date())
    vacinadas = dados_vacinacao.loc[filtro, 'aplicadas_dia']
    vacinadas = 'indisponível' if vacinadas.empty else f'{vacinadas.item():7,.0f}'.replace(',', '.')

    filtro = (dados_estado.data.dt.date == hoje.date())

    total_casos = dados_estado.loc[filtro, 'total_casos']
    total_casos = 'indisponível' if total_casos.empty else f'{total_casos.item():7,.0f}'.replace(',', '.')

    casos_dia = dados_estado.loc[filtro, 'casos_dia']
    casos_dia = 'indisponível' if casos_dia.empty else f'{casos_dia.item():7,.0f}'.replace(',', '.')

    total_obitos = dados_estado.loc[filtro, 'total_obitos']
    total_obitos = 'indisponível' if total_obitos.empty else f'{total_obitos.item():7,.0f}'.replace(',', '.')

    obitos_dia = dados_estado.loc[filtro, 'obitos_dia']
    obitos_dia = 'indisponível' if obitos_dia.empty else f'{obitos_dia.item():7,.0f}'.replace(',', '.')

    letalidade_atual = dados_estado.loc[filtro, 'letalidade']
    letalidade_atual = 'indisponível' if letalidade_atual.empty else f'{letalidade_atual.item():7.2f}%'.replace('.', ',')

    leitos_covid = internacoes.loc[(internacoes.drs == 'Estado de São Paulo') & (internacoes.data.dt.date == hoje.date()), 'total_covid_uti_ultimo_dia']
    leitos_covid = 'indisponível' if leitos_covid.empty else f'{leitos_covid.item():7,.0f}'.replace(',', '.')

    ocupacao_uti = leitos_estaduais.loc[leitos_estaduais.data.dt.date == hoje.date(), 'sp_uti']
    ocupacao_uti = 'indisponível' if ocupacao_uti.empty else f'{ocupacao_uti.item():7.1f}%'.replace('.', ',')

    estado = [vacinadas,
              total_casos,
              casos_dia,
              total_obitos,
              obitos_dia,
              letalidade_atual,
              leitos_covid,
              ocupacao_uti,
              isolamento_atual]

    filtro = (isolamento.município == 'São Paulo') & (isolamento.data.dt.date == hoje.date() - timedelta(days=1))
    isolamento_atual = isolamento.loc[filtro, 'isolamento']
    isolamento_atual = 'indisponível' if isolamento_atual.empty else f'{isolamento_atual.item():7.0f}%'.replace('.', ',')

    filtro = (dados_vacinacao.municipio == 'SAO PAULO') & (dados_vacinacao.data.dt.date == hoje.date())
    vacinadas = dados_vacinacao.loc[filtro, 'aplicadas_dia']
    vacinadas = 'indisponível' if vacinadas.empty else f'{vacinadas.item():7,.0f}'.replace(',', '.')

    filtro = (dados_munic.nome_munic == 'São Paulo') & (dados_munic.datahora.dt.date == hoje.date())

    total_casos = dados_munic.loc[filtro, 'casos']
    total_casos = 'indisponível' if total_casos.empty else f'{total_casos.item():7,.0f}'.replace(',', '.')

    casos_dia = dados_munic.loc[filtro, 'casos_novos']
    casos_dia = 'indisponível' if casos_dia.empty else f'{casos_dia.item():7,.0f}'.replace(',', '.')

    total_obitos = dados_munic.loc[filtro, 'obitos']
    total_obitos = 'indisponível' if total_obitos.empty else f'{total_obitos.item():7,.0f}'.replace(',', '.')

    obitos_dia = dados_munic.loc[filtro, 'obitos_novos']
    obitos_dia = 'indisponível' if obitos_dia.empty else f'{obitos_dia.item():7,.0f}'.replace(',', '.')

    letalidade_atual = dados_munic.loc[filtro, 'letalidade']
    letalidade_atual = 'indisponível' if letalidade_atual.empty else f'{letalidade_atual.item() * 100:7.2f}%'.replace('.', ',')

    leitos_covid = internacoes.loc[(internacoes.drs == 'Município de São Paulo') & (internacoes.data.dt.date == hoje.date()), 'total_covid_uti_ultimo_dia']
    leitos_covid = 'indisponível' if leitos_covid.empty else f'{leitos_covid.item():7,.0f}'.replace(',', '.')

    ocupacao_uti = internacoes.loc[(internacoes.drs == 'Município de São Paulo') & (internacoes.data.dt.date == hoje.date()), 'ocupacao_leitos_ultimo_dia']
    ocupacao_uti = 'indisponível' if ocupacao_uti.empty else f'{ocupacao_uti.item():7.1f}%'.replace('.', ',')

    cidade = [vacinadas,
              total_casos,
              casos_dia,
              total_obitos,
              obitos_dia,
              letalidade_atual,
              leitos_covid,
              ocupacao_uti,
              isolamento_atual]

    fig = go.Figure(data=[go.Table(header=dict(values=cabecalho,
                                               fill_color='#00aabb',
                                               font=dict(color='white'),
                                               align=['right', 'right', 'right'],
                                               line=dict(width=5)),
                                   cells=dict(values=[info, estado, cidade],
                                              fill_color='lavender',
                                              align='right',
                                              line=dict(width=5)),
                                   columnwidth=[1, 1, 1])])

    fig.update_layout(
        font=dict(size=15, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=30, pad=5),
        annotations=[dict(x=0, y=0, showarrow=False, font=dict(size=13),
                          text='<i><b>Fonte:</b> <a href = "https://www.seade.gov.br/coronavirus/">'
                               'Governo do Estado de São Paulo</a></i>')],
        height=415
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/resumo.html', include_plotlyjs='directory', auto_open=False)

    fig.update_layout(
        font=dict(size=13, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=30, pad=5),
        annotations=[dict(x=0, y=0)],
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/resumo-mobile.html', include_plotlyjs='directory', auto_open=False)


def _formata_variacao(v, retorna_texto=False):
    if math.isnan(v) or v is None:
        if retorna_texto:
            return 'indisponível'
        else:
            return math.nan

    return f'+{v:02.1f}%'.replace('.', ',') if v >= 0 else f'{v:02.1f}%'.replace('.', ',')


def _formata_semana_ordinal(data):
    semana = int(f'{data:%W}')

    if semana == 0:
        last_year = data.year - 1
        data = pd.to_datetime('31/12/' + str(last_year), format='%d/%m/%Y')
        semana = int(data.strftime('%W'))

    return semana + 1 if data.year == 2020 else semana


def gera_resumo_semanal(evolucao_cidade, evolucao_estado):
    # %W: semana começa na segunda-feira
    hoje = data_processamento_estado
    hoje_formatado = _formata_semana_ordinal(hoje)

    # %U: semana começa no domingo
    hoje = data_processamento_estado - timedelta(days=1)
    semana = _formata_semana_extenso(_converte_semana(hoje), inclui_ano=False)

    cabecalho = [f'<b>{hoje_formatado}ª semana<br>epidemiológica</b>',
                 f'<b>Estado de SP</b><br>{semana}',
                 f'<b>Cidade de SP</b><br>{semana}']

    semana = _formata_semana_extenso(_converte_semana(hoje), inclui_ano=True)

    info = ['<b>Vacinadas</b>', '<b>Variação</b>',
            '<b>Casos</b>', '<b>Variação</b>',
            '<b>Óbitos</b>', '<b>Variação</b>',
            '<b>Internações</b>', '<b>Variação</b>',
            '<b>Ocupação de UTIs</b>', '<b>Variação</b>',
            '<b>Isolamento</b>', '<b>Variação</b>']

    num_semana = evolucao_estado.index[evolucao_estado.data == semana].item()

    vacinadas_semana = evolucao_estado.loc[num_semana, 'vacinadas_semana']
    vacinadas_semana = 'indisponível' if math.isnan(vacinadas_semana) else f'{vacinadas_semana.item():7,.0f}'.replace(',', '.')

    casos_semana = evolucao_estado.loc[num_semana, 'casos_semana']
    casos_semana = 'indisponível' if math.isnan(casos_semana) else f'{casos_semana.item():7,.0f}'.replace(',', '.')

    obitos_semana = evolucao_estado.loc[num_semana, 'obitos_semana']
    obitos_semana = 'indisponível' if math.isnan(obitos_semana) else f'{obitos_semana.item():7,.0f}'.replace(',', '.')

    internacoes = evolucao_estado.loc[num_semana, 'internacoes']
    internacoes = 'indisponível' if math.isnan(internacoes) else f'{internacoes.item():7,.0f}'.replace(',', '.')

    uti = evolucao_estado.loc[num_semana, 'uti']
    uti = 'indisponível' if math.isnan(uti) else f'{uti.item():7.1f}%'.replace('.', ',')

    isolamento_atual = evolucao_estado.loc[num_semana, 'isolamento_atual']
    isolamento_atual = 'indisponível' if math.isnan(isolamento_atual) else f'{isolamento_atual.item():7.1f}%'.replace('.', ',')

    estado = [vacinadas_semana,  # Vacinadas
              '<i>' + _formata_variacao(evolucao_estado.loc[num_semana, 'variacao_vacinadas'], retorna_texto=True) + '</i>',  # Variação vacinadas
              casos_semana,  # Casos
              '<i>' + _formata_variacao(evolucao_estado.loc[num_semana, 'variacao_casos'], retorna_texto=True) + '</i>',  # Variação casos
              obitos_semana,  # óbitos
              '<i>' + _formata_variacao(evolucao_estado.loc[num_semana, 'variacao_obitos'], retorna_texto=True) + '</i>',  # Variação óbitos
              internacoes,  # Internações
              '<i>' + _formata_variacao(evolucao_estado.loc[num_semana, 'variacao_internacoes'], retorna_texto=True) + '</i>',  # Variação de internações
              uti,  # Ocupação de UTIs
              '<i>' + _formata_variacao(evolucao_estado.loc[num_semana, 'variacao_uti'], retorna_texto=True) + '</i>',  # Variação ocupação de UTIs
              isolamento_atual, # Isolamento social
              '<i>' + _formata_variacao(evolucao_estado.loc[num_semana, 'variacao_isolamento'], retorna_texto=True) + '</i>']  # Variação isolamento

    num_semana = evolucao_cidade.index[evolucao_cidade.data == semana].item()

    vacinadas_semana = evolucao_cidade.loc[num_semana, 'vacinadas_semana']
    vacinadas_semana = 'indisponível' if math.isnan(vacinadas_semana) else f'{vacinadas_semana.item():7,.0f}'.replace(',', '.')

    casos_semana = evolucao_cidade.loc[num_semana, 'casos_semana']
    casos_semana = 'indisponível' if math.isnan(casos_semana) else f'{casos_semana.item():7,.0f}'.replace(',', '.')

    obitos_semana = evolucao_cidade.loc[num_semana, 'obitos_semana']
    obitos_semana = 'indisponível' if math.isnan(obitos_semana) else f'{obitos_semana.item():7,.0f}'.replace(',', '.')

    internacoes = evolucao_cidade.loc[num_semana, 'internacoes']
    internacoes = 'indisponível' if math.isnan(internacoes) else f'{internacoes.item():7,.0f}'.replace(',', '.')

    uti = evolucao_cidade.loc[num_semana, 'uti']
    uti = 'indisponível' if math.isnan(uti) else f'{uti.item():7.1f}%'.replace('.', ',')

    isolamento_atual = evolucao_cidade.loc[num_semana, 'isolamento_atual']
    isolamento_atual = 'indisponível' if math.isnan(isolamento_atual) else f'{isolamento_atual.item():7.1f}%'.replace('.', ',')

    cidade = [vacinadas_semana,  # Vacinadas
              '<i>' + _formata_variacao(evolucao_cidade.loc[num_semana, 'variacao_vacinadas'], retorna_texto=True) + '</i>',  # Variação vacinadas
              casos_semana,  # Casos
              '<i>' + _formata_variacao(evolucao_cidade.loc[num_semana, 'variacao_casos'], retorna_texto=True) + '</i>',  # Variação casos
              obitos_semana,  # óbitos
              '<i>' + _formata_variacao(evolucao_cidade.loc[num_semana, 'variacao_obitos'], retorna_texto=True) + '</i>',  # Variação óbitos
              internacoes,  # Internações
              '<i>' + _formata_variacao(evolucao_cidade.loc[num_semana, 'variacao_internacoes'], retorna_texto=True) + '</i>',  # Variação de internações
              uti,  # Ocupação de UTIs
              '<i>' + _formata_variacao(evolucao_cidade.loc[num_semana, 'variacao_uti'], retorna_texto=True) + '</i>',  # Variação ocupação de UTIs
              isolamento_atual,  # Isolamento social
              '<i>' + _formata_variacao(evolucao_cidade.loc[num_semana, 'variacao_isolamento'], retorna_texto=True) + '</i>']  # Variação isolamento

    fig = go.Figure(data=[go.Table(header=dict(values=cabecalho,
                                               fill_color='#00aabb',
                                               font=dict(color='white'),
                                               align=['right', 'right', 'right'],
                                               line=dict(width=5)),
                                   cells=dict(values=[info, estado, cidade],
                                              fill_color='lavender',
                                              align='right',
                                              line=dict(width=5)),
                                   columnwidth=[1, 1, 1])])

    fig.update_layout(
        font=dict(size=15, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=30, pad=5),
        annotations=[dict(x=0, y=0, showarrow=False, font=dict(size=13),
                          text='<i><b>Fonte:</b> <a href = "https://www.seade.gov.br/coronavirus/">'
                               'Governo do Estado de São Paulo</a></i>')],
        height=515
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/resumo-semanal.html', include_plotlyjs='directory', auto_open=False)

    fig.update_layout(
        font=dict(size=13, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=30, pad=5),
        annotations=[dict(x=0, y=0)],
        height=500
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/resumo-semanal-mobile.html', include_plotlyjs='directory', auto_open=False)


def gera_casos_estado(dados):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(x=dados['dia'], y=dados['total_casos'], line=dict(color='blue'),
                             mode='lines+markers', name='casos confirmados'))

    fig.add_trace(go.Bar(x=dados['dia'], y=dados['casos_dia'], marker_color='blue',
                         name='casos por dia'))

    fig.add_trace(go.Scatter(x=dados['dia'], y=dados['total_obitos'], line=dict(color='red'),
                             mode='lines+markers', name='total de óbitos'))

    fig.add_trace(go.Bar(x=dados['dia'], y=dados['obitos_dia'], marker_color='red',
                         name='óbitos por dia', visible='legendonly'))

    fig.add_trace(go.Scatter(x=dados['dia'], y=dados['letalidade'], line=dict(color='green'),
                             mode='lines+markers', name='letalidade', hovertemplate='%{y:.2f}%'),
                  secondary_y=True)

    d = dados.dia.size

    frames = [dict(data=[dict(type='scatter', x=dados.dia[:d + 1], y=dados.total_casos[:d + 1]),
                         dict(type='bar', x=dados.dia[:d + 1], y=dados.casos_dia[:d + 1]),
                         dict(type='scatter', x=dados.dia[:d + 1], y=dados.total_obitos[:d + 1]),
                         dict(type='bar', x=dados.dia[:d + 1], y=dados.obitos_dia[:d + 1]),
                         dict(type='scatter', x=dados.dia[:d + 1], y=dados.letalidade[:d + 1])],
                   traces=[0, 1, 2, 3, 4],
                   ) for d in range(0, d)]

    fig.frames = frames

    botoes = [dict(label='Animar', method='animate',
                   args=[None, dict(frame=dict(duration=200, redraw=True), fromcurrent=True, mode='immediate')])]

    fig.update_layout(
        font=dict(family='Roboto'),
        title='Casos confirmados de Covid-19 no Estado de São Paulo' +
              '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
              'Governo do Estado de São Paulo</a></i>',
        xaxis_tickangle=45,
        hovermode='x unified',
        hoverlabel={'namelength': -1},  # para não truncar o nome de cada trace no hover
        template='plotly',
        updatemenus=[dict(type='buttons', showactive=False,
                          x=0.05, y=0.95,
                          xanchor='left', yanchor='top',
                          pad=dict(t=0, r=10), buttons=botoes)],
        height=600
    )

    fig.update_yaxes(title_text='Número de casos ou óbitos', secondary_y=False)
    fig.update_yaxes(title_text='Taxa de letalidade (%)', secondary_y=True)

    # fig.show()

    pio.write_html(fig, file='docs/graficos/casos-estado.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)

    # versão mobile
    fig.update_traces(selector=dict(type='scatter'), mode='lines')

    fig.update_xaxes(nticks=10)

    fig.update_layout(
        showlegend=False,
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=10),
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/casos-estado-mobile.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)


def gera_casos_cidade(dados):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(x=dados['dia'], y=dados['confirmados'], line=dict(color='blue'),
                             mode='lines+markers', name='casos confirmados'))

    fig.add_trace(go.Bar(x=dados['dia'], y=dados['casos_dia'], marker_color='blue',
                         name='casos confirmados por dia'))

    fig.add_trace(go.Scatter(x=dados['dia'], y=dados['óbitos'], line=dict(color='red'),
                             mode='lines+markers', name='óbitos confirmados'))

    fig.add_trace(go.Bar(x=dados['dia'], y=dados['óbitos_dia'], marker_color='red',
                         name='óbitos confirmados por dia', visible='legendonly'))

    fig.add_trace(go.Scatter(x=dados['dia'], y=dados['letalidade'], line=dict(color='green'),
                             mode='lines+markers', name='letalidade', hovertemplate='%{y:.2f}%'),
                  secondary_y=True)

    qtde_dias = dados.dia.size

    frames = [dict(data=[dict(type='scatter', x=dados.dia[:d + 1], y=dados.confirmados[:d + 1]),
                         dict(type='bar', x=dados.dia[:d + 1], y=dados.casos_dia[:d + 1]),
                         dict(type='scatter', x=dados.dia[:d + 1], y=dados.óbitos[:d + 1]),
                         dict(type='bar', x=dados.dia[:d + 1], y=dados.óbitos_dia[:d + 1]),
                         dict(type='scatter', x=dados.dia[:d + 1], y=dados.letalidade[:d + 1])],
                   traces=[0, 1, 2, 3, 4],
                   ) for d in range(0, qtde_dias)]

    fig.frames = frames

    botoes = [dict(label='Animar', method='animate',
                   args=[None, dict(frame=dict(duration=200, redraw=True), fromcurrent=True, mode='immediate')])]

    fig.update_layout(
        font=dict(family='Roboto'),
        title='Casos confirmados de Covid-19 na cidade de São Paulo' +
              '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
              'Governo do Estado de São Paulo</a></i>',
        xaxis_tickangle=45,
        hovermode='x unified',
        hoverlabel={'namelength': -1},  # para não truncar o nome de cada trace no hover
        template='plotly',
        updatemenus=[dict(type='buttons', showactive=False,
                          x=0.05, y=0.95,
                          xanchor='left', yanchor='top',
                          pad=dict(t=0, r=10), buttons=botoes)],
        height=600
    )

    fig.update_yaxes(title_text='Número de casos ou óbitos', secondary_y=False)
    fig.update_yaxes(title_text='Taxa de letalidade (%)', secondary_y=True)

    # fig.show()

    pio.write_html(fig, file='docs/graficos/casos-cidade.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)

    # versão mobile
    fig.update_traces(selector=dict(type='scatter'), mode='lines')

    fig.update_xaxes(nticks=10)

    fig.update_layout(
        showlegend=False,
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=20),
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/casos-cidade-mobile.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)


def gera_doencas_preexistentes_casos(doencas):
    idades = list(doencas.reset_index('idade').idade.unique())

    casos_ignorados_m = [doencas.xs(('CONFIRMADO', 'FEMININO', i, 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO',
                                     'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO',
                                     'IGNORADO', 'IGNORADO'), level=('covid19', 'sexo', 'idade', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica',
                                     'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera',
                                     'sindrome_de_down')).asma.sum() for i in idades]
    casos_ignorados_h = [doencas.xs(('CONFIRMADO', 'MASCULINO', i, 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO',
                                     'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO',
                                     'IGNORADO', 'IGNORADO'), level=('covid19', 'sexo', 'idade', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica',
                                     'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera',
                                     'sindrome_de_down')).asma.sum() for i in idades]

    casos_sem_doencas_m = [doencas.xs(('CONFIRMADO', 'FEMININO', i, 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO',
                                       'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO'), level=('covid19', 'sexo', 'idade', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica',
                                       'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera',
                                       'sindrome_de_down')).asma.sum() for i in idades]
    casos_sem_doencas_h = [doencas.xs(('CONFIRMADO', 'MASCULINO', i, 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO',
                                       'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO'), level=('covid19', 'sexo', 'idade', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica',
                                       'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera',
                                       'sindrome_de_down')).asma.sum() for i in idades]

    casos_com_doencas_m = []
    casos_com_doencas_h = []

    for d in doencas.columns:
        casos_com_doencas_m.append(
            [doencas.xs(('CONFIRMADO', 'FEMININO', i, 'SIM'), level=('covid19', 'sexo', 'idade', d))[d].sum() for i in
             idades])
        casos_com_doencas_h.append(
            [doencas.xs(('CONFIRMADO', 'MASCULINO', i, 'SIM'), level=('covid19', 'sexo', 'idade', d))[d].sum() for i in
             idades])

    # para os dados femininos, todos os valores precisam ser negativados
    casos_ignorados_m_neg = [-valor for valor in casos_ignorados_m]
    casos_sem_doencas_m_neg = [-valor for valor in casos_sem_doencas_m]
    casos_com_doencas_m_neg = [[-valor for valor in lista] for lista in casos_com_doencas_m]

    fig = go.Figure()

    cont = 0

    for lista_m in casos_com_doencas_m_neg:
        fig.add_trace(go.Bar(x=lista_m, y=idades, orientation='h',
                             hoverinfo='text+y+name', text=casos_com_doencas_m[cont],
                             marker_color='red', name=doencas.columns[cont],
                             visible=True if cont == 0 else 'legendonly'))
        cont = cont + 1

    cont = 0

    for lista_h in casos_com_doencas_h:
        fig.add_trace(go.Bar(x=lista_h, y=idades, orientation='h', hoverinfo='x+y+name',
                             marker_color='blue', name=doencas.columns[cont],
                             visible=True if cont == 0 else 'legendonly'))
        cont = cont + 1

    fig.add_trace(go.Bar(x=casos_sem_doencas_m_neg, y=idades, orientation='h',
                         hoverinfo='text+y+name', text=casos_sem_doencas_m,
                         marker_color='red', name='sem doenças<br>preexistentes', visible='legendonly'))

    fig.add_trace(go.Bar(x=casos_sem_doencas_h, y=idades, orientation='h', hoverinfo='x+y+name',
                         marker_color='blue', name='sem doenças<br>preexistentes', visible='legendonly'))

    fig.add_trace(go.Bar(x=casos_ignorados_m_neg, y=idades, orientation='h',
                         hoverinfo='text+y+name', text=casos_ignorados_m,
                         marker_color='red', name='ignorado', visible='legendonly'))

    fig.add_trace(go.Bar(x=casos_ignorados_h, y=idades, orientation='h', hoverinfo='x+y+name',
                         marker_color='blue', name='ignorado', visible='legendonly'))

    fig.update_layout(
        font=dict(family='Roboto'),
        title='Doenças preexistentes nos casos confirmados de Covid-19 no Estado de São Paulo' +
              '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
              'Governo do Estado de São Paulo</a></i>',
        yaxis_title='Idade',
        xaxis_title='Mulheres | Homens',
        hovermode='y',
        hoverlabel={'namelength': -1},  # para não truncar o nome de cada trace no hover
        template='plotly',
        barmode='overlay',
        bargap=0.1,
        height=600
    )

    fig.update_yaxes(range=[0, 105], tickvals=[*range(0, 105, 5)])

    pio.write_html(fig, file='docs/graficos/doencas-casos.html', include_plotlyjs='directory',
                   auto_open=False, auto_play=False)

    # versão mobile
    fig.update_yaxes(range=[0, 105], tickvals=[*range(0, 105, 10)])

    fig.update_layout(
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=10),
        height=400
    )

    pio.write_html(fig, file='docs/graficos/doencas-casos-mobile.html', include_plotlyjs='directory',
                   auto_open=False, auto_play=False)


def gera_doencas_preexistentes_obitos(doencas):
    idades = list(doencas.reset_index('idade').idade.unique())

    obitos_ignorados_m = [doencas.xs(('CONFIRMADO', 'FEMININO', i, 1, 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO',
                                      'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO',
                                      'IGNORADO', 'IGNORADO', 'IGNORADO'), level=('covid19', 'sexo', 'idade', 'obito', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica',
                                      'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera',
                                      'sindrome_de_down')).asma.sum() for i in idades]
    obitos_ignorados_h = [doencas.xs(('CONFIRMADO', 'MASCULINO', i, 1, 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO',
                                      'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO', 'IGNORADO',
                                      'IGNORADO', 'IGNORADO', 'IGNORADO'), level=('covid19', 'sexo', 'idade', 'obito', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica',
                                      'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera',
                                      'sindrome_de_down')).asma.sum() for i in idades]

    obitos_sem_doencas_m = [doencas.xs(('CONFIRMADO', 'FEMININO', i, 1, 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO',
                                        'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO'), level=('covid19', 'sexo', 'idade', 'obito', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica',
                                        'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera',
                                        'sindrome_de_down')).asma.sum() for i in idades]
    obitos_sem_doencas_h = [doencas.xs(('CONFIRMADO', 'MASCULINO', i, 1, 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO',
                                       'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO', 'NÃO'), level=('covid19', 'sexo', 'idade', 'obito', 'asma', 'cardiopatia', 'diabetes', 'doenca_hematologica', 'doenca_hepatica',
                                       'doenca_neurologica', 'doenca_renal', 'imunodepressao', 'obesidade', 'outros', 'pneumopatia', 'puerpera',
                                       'sindrome_de_down')).asma.sum() for i in idades]

    obitos_com_doencas_m = []
    obitos_com_doencas_h = []

    for d in doencas.columns:
        obitos_com_doencas_m.append([doencas.xs(('CONFIRMADO', 'FEMININO', i, 1, 'SIM'),
                                                level=('covid19', 'sexo', 'idade', 'obito', d))[d].sum() for i in
                                     idades])
        obitos_com_doencas_h.append([doencas.xs(('CONFIRMADO', 'MASCULINO', i, 1, 'SIM'),
                                                level=('covid19', 'sexo', 'idade', 'obito', d))[d].sum() for i in
                                     idades])

    # para os dados femininos, todos os valores precisam ser negativados
    obitos_ignorados_m_neg = [-valor for valor in obitos_ignorados_m]
    obitos_sem_doencas_m_neg = [-valor for valor in obitos_sem_doencas_m]
    obitos_com_doencas_m_neg = [[-valor for valor in lista] for lista in obitos_com_doencas_m]

    fig = go.Figure()

    cont = 0

    for lista_m in obitos_com_doencas_m_neg:
        fig.add_trace(go.Bar(x=lista_m, y=idades, orientation='h',
                             hoverinfo='text+y+name', text=obitos_com_doencas_m[cont],
                             marker_color='red', name=doencas.columns[cont],
                             visible=True if cont == 0 else 'legendonly'))
        cont = cont + 1

    cont = 0

    for lista_h in obitos_com_doencas_h:
        fig.add_trace(go.Bar(x=lista_h, y=idades, orientation='h', hoverinfo='x+y+name',
                             marker_color='blue', name=doencas.columns[cont],
                             visible=True if cont == 0 else 'legendonly'))
        cont = cont + 1

    fig.add_trace(go.Bar(x=obitos_sem_doencas_m_neg, y=idades, orientation='h',
                         hoverinfo='text+y+name', text=obitos_sem_doencas_m,
                         marker_color='red', name='sem doenças<br>preexistentes', visible='legendonly'))

    fig.add_trace(go.Bar(x=obitos_sem_doencas_h, y=idades, orientation='h', hoverinfo='x+y+name',
                         marker_color='blue', name='sem doenças<br>preexistentes', visible='legendonly'))

    fig.add_trace(go.Bar(x=obitos_ignorados_m_neg, y=idades, orientation='h',
                         hoverinfo='text+y+name', text=obitos_ignorados_m,
                         marker_color='red', name='ignorado', visible='legendonly'))

    fig.add_trace(go.Bar(x=obitos_ignorados_h, y=idades, orientation='h', hoverinfo='x+y+name',
                         marker_color='blue', name='ignorado', visible='legendonly'))

    fig.update_layout(
        font=dict(family='Roboto'),
        title='Doenças preexistentes nos óbitos confirmados por Covid-19 no Estado de São Paulo' +
              '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
              'Governo do Estado de São Paulo</a></i>',
        yaxis_title='Idade',
        xaxis_title='Mulheres | Homens',
        hovermode='y',
        hoverlabel={'namelength': -1},  # para não truncar o nome de cada trace no hover
        template='plotly',
        barmode='overlay',
        bargap=0.1,
        height=600
    )

    fig.update_yaxes(range=[0, 105], tickvals=[*range(0, 105, 5)])

    pio.write_html(fig, file='docs/graficos/doencas-obitos.html', include_plotlyjs='directory',
                   auto_open=False, auto_play=False)

    # versão mobile
    fig.update_yaxes(range=[0, 105], tickvals=[*range(0, 105, 10)])

    fig.update_layout(
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=10),
        height=400
    )

    pio.write_html(fig, file='docs/graficos/doencas-obitos-mobile.html', include_plotlyjs='directory',
                   auto_open=False, auto_play=False)


def gera_casos_obitos_por_raca_cor(dados_raciais):
    racas_cores = list(dados_raciais.reset_index('raca_cor').raca_cor.unique())

    casos = [dados_raciais.xs(rc, level='raca_cor').contagem.sum() for rc in racas_cores]
    casos_perc = ['{:02.1f}%'.format((c / sum(casos)) * 100) for c in casos]

    obitos = [dados_raciais.xs((1, rc), level=('obito', 'raca_cor')).contagem.sum() for rc in racas_cores]
    obitos_perc = ['{:02.1f}%'.format((o / sum(obitos)) * 100) for o in obitos]

    fig = go.Figure()

    fig.add_trace(go.Bar(x=casos, y=racas_cores,
                         orientation='h', hoverinfo='x+y+name',
                         textposition='auto', text=casos_perc,
                         marker_color='blue', name='casos', visible=True))

    fig.add_trace(go.Bar(x=obitos, y=racas_cores,
                         orientation='h', hoverinfo='x+y+name',
                         textposition='auto', text=obitos_perc,
                         marker_color='red', name='óbitos', visible=True))

    fig.update_layout(
        font=dict(family='Roboto'),
        title='Raça/cor nos casos e óbitos confirmados por Covid-19 no Estado de São Paulo' +
              '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
              'Governo do Estado de São Paulo</a></i>',
        xaxis_title='Casos ou óbitos',
        xaxis_tickangle=30,
        hovermode='y',
        barmode='stack',
        bargap=0.1,
        hoverlabel={'namelength': -1},
        template='plotly',
        height=600
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/raca-cor.html', include_plotlyjs='directory',
                   auto_open=False, auto_play=False)

    # versão mobile
    fig.update_layout(
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=10),
        height=400
    )

    pio.write_html(fig, file='docs/graficos/raca-cor-mobile.html', include_plotlyjs='directory',
                   auto_open=False, auto_play=False)


def gera_isolamento_grafico(isolamento):
    fig = go.Figure()

    # lista de municípios em ordem de maior índice de isolamento
    l_municipios = list(
        isolamento.sort_values(by=['data', 'isolamento', 'município'], ascending=False).município.unique())

    # series em vez de list, para que seja possível utilizar o método isin
    s_municipios = pd.Series(l_municipios)

    titulo_a = 'Índice de adesão ao isolamento social - '
    titulo_b = '<br><i>Fonte: <a href = "https://www.saopaulo.sp.gov.br/coronavirus/isolamento/">Governo do Estado de São Paulo</a></i>'

    cidades_iniciais = ['Estado de São Paulo', 'São Paulo', 'Guarulhos', 'Osasco', 'Jundiaí', 'Caieiras',
                        'Campinas', 'Santo André', 'Mauá', 'Francisco Morato', 'Poá']

    for m in l_municipios:
        grafico = isolamento[isolamento.município == m]

        if m in cidades_iniciais:
            fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['isolamento'], name=m,
                                     mode='lines+markers', hovertemplate='%{y:.0f}%', visible=True))
        else:
            fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['isolamento'], name=m,
                                     mode='lines+markers+text', textposition='top center',
                                     text=grafico['isolamento'].apply(lambda i: str(i) + '%'),
                                     hovertemplate='%{y:.0f}%', visible=False))

    opcao_metro = dict(label='Região Metropolitana',
                       method='update',
                       args=[{'visible': s_municipios.isin(cidades_iniciais)},
                             {'title.text': titulo_a + 'Região Metropolitana' + titulo_b},
                             {'showlegend': True}])

    opcao_estado = dict(label='Estado de São Paulo',
                        method='update',
                        args=[{'visible': s_municipios.isin(['Estado de São Paulo'])},
                              {'title.text': titulo_a + 'Estado de São Paulo' + titulo_b},
                              {'showlegend': False}])

    def cria_lista_opcoes(cidade):
        return dict(label=cidade,
                    method='update',
                    args=[{'visible': s_municipios.isin([cidade])},
                          {'title.text': titulo_a + cidade + titulo_b},
                          {'showlegend': False}])

    fig.update_layout(
        font=dict(family='Roboto'),
        title=titulo_a + 'Região Metropolitana' + titulo_b,
        xaxis_tickangle=45,
        yaxis_title='Índice de isolamento social (%)',
        hovermode='x unified',
        hoverlabel={'namelength': -1},  # para não truncar o nome de cada trace no hover
        template='plotly',
        updatemenus=[go.layout.Updatemenu(active=0,
                                          buttons=[opcao_metro, opcao_estado] + list(
                                              s_municipios.apply(lambda m: cria_lista_opcoes(m))),
                                          x=0.001, xanchor='left',
                                          y=0.990, yanchor='top')],
        height=600
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/isolamento.html', include_plotlyjs='directory', auto_open=False)

    # versão mobile
    fig.update_traces(mode='lines+text')

    fig.update_xaxes(nticks=10)

    fig.update_layout(
        showlegend=False,
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=10),
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/isolamento-mobile.html', include_plotlyjs='directory', auto_open=False)


def gera_isolamento_tabela(isolamento):
    dados = isolamento.loc[isolamento.data == isolamento.data.max(), ['data', 'município', 'isolamento']]
    dados.sort_values(by=['isolamento', 'município'], ascending=False, inplace=True)

    cabecalho = ['<b>Cidade</b>',
                 '<b>Isolamento</b><br><i>' + dados.data.iloc[0].strftime('%d/%m/%Y') + '</i>']

    fig = go.Figure(data=[go.Table(header=dict(values=cabecalho,
                                               fill_color='#00aabb',
                                               font=dict(color='white'),
                                               align='right',
                                               line=dict(width=5)),
                                   cells=dict(values=[dados.município, dados.isolamento.map('{:02.0f}%'.format)],
                                              fill_color='lavender',
                                              align='right',
                                              line=dict(width=5),
                                              height=30),
                                   columnwidth=[1, 1])])

    fig.update_layout(
        font=dict(size=15, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=30, pad=5),
        annotations=[dict(x=0, y=1.05, showarrow=False, font=dict(size=13),
                          text='<i><b>Fonte:</b> <a href = "https://www.saopaulo.sp.gov.br/coronavirus/isolamento/">'
                               'Governo do Estado de São Paulo</a></i>')],
        height=600
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/tabela-isolamento.html', include_plotlyjs='directory', auto_open=False)

    fig.update_layout(
        font=dict(size=13, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=30, pad=5),
        annotations=[dict(x=0, y=1.05)],
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/tabela-isolamento-mobile.html', include_plotlyjs='directory',
                   auto_open=False)


def gera_evolucao_estado(evolucao_estado):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    grafico = evolucao_estado

    fig.add_trace(go.Scatter(x=grafico['data'], y=grafico['isolamento'], line=dict(color='orange'),
                             name='isolamento médio<br>de 2 semanas atrás', hovertemplate='%{y:.2f}%',
                             mode='lines+markers+text', textposition='top center',
                             text=grafico['variacao_isolamento_2sem'].apply(lambda v: _formata_variacao(v))),
                  secondary_y=True)

    fig.add_trace(go.Scatter(x=grafico['data'], y=grafico['uti'], line=dict(color='green'),
                             name='taxa média de<br>ocupação de UTI', hovertemplate='%{y:.2f}%',
                             mode='lines+markers+text', textposition='top center',
                             text=grafico['variacao_uti'].apply(lambda v: _formata_variacao(v))),
                  secondary_y=True)

    fig.add_trace(go.Scatter(x=grafico['data'], y=grafico['perc_vac_semana'], line=dict(color='black'),
                             name='população vacinada', hovertemplate='%{y:.2f}%',
                             mode='lines+markers+text', textposition='top center',
                             text=grafico['variacao_perc_vac'].apply(lambda v: _formata_variacao(v))),
                  secondary_y=True)

    fig.add_trace(go.Bar(x=grafico['data'], y=grafico['casos_semana'], marker_color='blue',
                         name='casos na<br>semana atual', textposition='outside',
                         text=grafico['variacao_casos'].apply(lambda v: _formata_variacao(v))))

    fig.add_trace(go.Bar(x=grafico['data'], y=grafico['obitos_semana'], marker_color='red',
                         name='óbitos na<br>semana atual', textposition='outside',
                         text=grafico['variacao_obitos'].apply(lambda v: _formata_variacao(v))))

    fig.add_trace(go.Bar(x=grafico['data'], y=grafico['vacinadas_semana'], visible='legendonly',
                         marker_color='black', textposition='outside', name='pessoas vacinadas<br>na semana atual',
                         text=grafico['variacao_vacinadas'].apply(lambda v: _formata_variacao(v))))

    d = grafico.data.size

    frames = [dict(data=[dict(type='scatter', x=grafico.data[:d + 1], y=grafico.isolamento[:d + 1]),
                         dict(type='scatter', x=grafico.data[:d + 1], y=grafico.uti[:d + 1]),
                         dict(type='scatter', x=grafico.data[:d + 1], y=grafico.perc_vac_semana[:d + 1]),
                         dict(type='bar', x=grafico.data[:d + 1], y=grafico.casos_semana[:d + 1]),
                         dict(type='bar', x=grafico.data[:d + 1], y=grafico.obitos_semana[:d + 1]),
                         dict(type='bar', x=grafico.data[:d + 1], y=grafico.vacinadas_semana[:d + 1])],
                   traces=[0, 1, 2, 3, 4, 5],
                   ) for d in range(0, d)]

    fig.frames = frames

    botoes = [dict(label='Animar', method='animate',
                   args=[None, dict(frame=dict(duration=400, redraw=True), fromcurrent=True, mode='immediate')])]

    fig.update_yaxes(title_text='Número de casos ou óbitos', secondary_y=False)
    fig.update_yaxes(title_text='Taxa média de isolamento há 2 semanas (%)', secondary_y=True)

    fig.update_layout(
        font=dict(family='Roboto'),
        title='Evolução da pandemia no Estado de São Paulo' +
              '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
              'Governo do Estado de São Paulo</a></i>',
        xaxis_tickangle=45,
        hovermode='x unified',
        hoverlabel={'namelength': -1},
        template='plotly',
        updatemenus=[dict(type='buttons', showactive=False,
                          x=0.05, y=0.95,
                          xanchor='left', yanchor='top',
                          pad=dict(t=0, r=10), buttons=botoes)],
        height=600
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/evolucao-estado.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)

    # versão mobile
    fig.update_traces(selector=dict(type='scatter'), mode='lines')

    fig.update_xaxes(nticks=5)

    fig.update_layout(
        showlegend=False,
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=10),
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/evolucao-estado-mobile.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)


def gera_evolucao_cidade(evolucao_cidade):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    grafico = evolucao_cidade

    fig.add_trace(go.Scatter(x=grafico['data'], y=grafico['isolamento'], line=dict(color='orange'),
                             name='isolamento médio<br>de 2 semanas atrás', hovertemplate='%{y:.2f}%',
                             mode='lines+markers+text', textposition='top center',
                             text=grafico['variacao_isolamento_2sem'].apply(lambda v: _formata_variacao(v))),
                  secondary_y=True)

    fig.add_trace(go.Scatter(x=grafico['data'], y=grafico['uti'], line=dict(color='green'),
                             name='taxa média de<br>ocupação de UTI', hovertemplate='%{y:.2f}%',
                             mode='lines+markers+text', textposition='top center',
                             text=grafico['variacao_uti'].apply(lambda v: _formata_variacao(v))),
                  secondary_y=True)

    fig.add_trace(go.Scatter(x=grafico['data'], y=grafico['perc_vac_semana'], line=dict(color='black'),
                             name='população vacinada', hovertemplate='%{y:.2f}%',
                             mode='lines+markers+text', textposition='top center',
                             text=grafico['variacao_perc_vac'].apply(lambda v: _formata_variacao(v))),
                  secondary_y=True)

    fig.add_trace(go.Bar(x=grafico['data'], y=grafico['casos_semana'], marker_color='blue',
                         name='casos na<br>semana atual', textposition='outside',
                         text=grafico['variacao_casos'].apply(lambda v: _formata_variacao(v))))

    fig.add_trace(go.Bar(x=grafico['data'], y=grafico['obitos_semana'], marker_color='red',
                         name='óbitos na<br>semana atual', textposition='outside',
                         text=grafico['variacao_obitos'].apply(lambda v: _formata_variacao(v))))

    fig.add_trace(go.Bar(x=grafico['data'], y=grafico['vacinadas_semana'], visible='legendonly',
                         marker_color='black', textposition='outside', name='pessoas vacinadas<br>na semana atual',
                         text=grafico['variacao_vacinadas'].apply(lambda v: _formata_variacao(v))))

    d = grafico.data.size

    frames = [dict(data=[dict(type='scatter', x=grafico.data[:d + 1], y=grafico.isolamento[:d + 1]),
                         dict(type='scatter', x=grafico.data[:d + 1], y=grafico.uti[:d + 1]),
                         dict(type='scatter', x=grafico.data[:d + 1], y=grafico.perc_vac_semana[:d + 1]),
                         dict(type='bar', x=grafico.data[:d + 1], y=grafico.casos_semana[:d + 1]),
                         dict(type='bar', x=grafico.data[:d + 1], y=grafico.obitos_semana[:d + 1]),
                         dict(type='bar', x=grafico.data[:d + 1], y=grafico.vacinadas_semana[:d + 1])],
                   traces=[0, 1, 2, 3, 4, 5],
                   ) for d in range(0, d)]

    fig.frames = frames

    botoes = [dict(label='Animar', method='animate',
                   args=[None, dict(frame=dict(duration=400, redraw=True), fromcurrent=True, mode='immediate')])]

    fig.update_yaxes(title_text='Número de casos ou óbitos', secondary_y=False)
    fig.update_yaxes(title_text='Taxa média de isolamento há 2 semanas (%)', secondary_y=True)

    fig.update_layout(
        font=dict(family='Roboto'),
        title='Evolução da pandemia na Cidade de São Paulo' +
              '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
              'Governo do Estado de São Paulo</a></i>',
        xaxis_tickangle=45,
        hovermode='x unified',
        hoverlabel={'namelength': -1},
        template='plotly',
        updatemenus=[dict(type='buttons', showactive=False,
                          x=0.05, y=0.95,
                          xanchor='left', yanchor='top',
                          pad=dict(t=0, r=10), buttons=botoes)],
        height=600
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/evolucao-cidade.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)

    # versão mobile
    fig.update_traces(selector=dict(type='scatter'), mode='lines')

    fig.update_xaxes(nticks=5)

    fig.update_layout(
        showlegend=False,
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=10),
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/evolucao-cidade-mobile.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)


def gera_leitos_estaduais(leitos):
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['rmsp_uti'],
                             mode='lines+markers', name='UTI<br>(região metropolitana)',
                             hovertemplate='%{y:.1f}%'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['rmsp_enfermaria'],
                             mode='lines+markers', name='enfermaria<br>(região metropolitana)',
                             hovertemplate='%{y:.1f}%'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['sp_uti'],
                             mode='lines+markers', name='UTI<br>(estado)', hovertemplate='%{y:.1f}%'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['sp_enfermaria'],
                             mode='lines+markers', name='enfermaria<br>(estado)', hovertemplate='%{y:.1f}%'))

    d = leitos.dia.size

    frames = [dict(data=[dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.rmsp_uti[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.rmsp_enfermaria[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.sp_uti[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.sp_enfermaria[:d + 1])],
                   traces=[0, 1, 2, 3],
                   ) for d in range(0, d)]

    fig.frames = frames

    botoes = [dict(label='Animar', method='animate',
                   args=[None, dict(frame=dict(duration=200, redraw=True), fromcurrent=True, mode='immediate')])]

    fig.update_layout(
        font=dict(family='Roboto'),
        title='Ocupação de leitos Covid-19 no Estado de São Paulo' +
              '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
              'Governo do Estado de São Paulo</a></i>',
        xaxis_tickangle=45,
        yaxis_title='Taxa de ocupação dos leitos (%)',
        hovermode='x unified',
        hoverlabel={'namelength': -1},  # para não truncar o nome de cada trace no hover
        template='plotly',
        updatemenus=[dict(type='buttons', showactive=False,
                          x=0.05, y=0.95,
                          xanchor='left', yanchor='top',
                          pad=dict(t=0, r=10), buttons=botoes)],
        height=600
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/leitos-estaduais.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)

    # versão mobile
    fig.update_traces(mode='lines')

    fig.update_xaxes(nticks=10)

    fig.update_layout(
        showlegend=False,
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=10),
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/leitos-estaduais-mobile.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)


def gera_drs(internacoes):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # lista de Departamentos Regionais de Saúde
    l_drs = list(internacoes.drs.sort_values(ascending=False).unique())

    # series em vez de list, para que seja possível utilizar o método isin
    s_drs = pd.Series(l_drs)

    titulo_a = 'Departamento Regional de Saúde - '
    titulo_b = '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">Governo do Estado de São Paulo</a></i>'

    for d in l_drs:
        grafico = internacoes[internacoes.drs == d]

        if d == 'Estado de São Paulo':
            mostrar = True
        else:
            mostrar = False

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['pacientes_uti_mm7d'],
                                 name='pacientes internados em leitos<br>de UTI para Covid-19 - média<br>móvel dos últimos 7 dias',
                                 mode='lines+markers', hovertemplate='%{y:.0f}', customdata=[d], visible=mostrar))

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['pacientes_uti_ultimo_dia'],
                                 name='pacientes internados em leitos<br>de UTI para Covid-19<br>no dia anterior',
                                 mode='lines+markers', hovertemplate='%{y:.0f}', customdata=[d], visible=mostrar))

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['total_covid_uti_mm7d'],
                                 name='leitos Covid-19 - média<br>móvel dos últimos 7 dias',
                                 mode='lines+markers', hovertemplate='%{y:.0f}', customdata=[d], visible=mostrar))

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['total_covid_uti_ultimo_dia'],
                                 name='leitos Covid-19<br>no dia anterior',
                                 mode='lines+markers', hovertemplate='%{y:.0f}', customdata=[d], visible=mostrar))

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['ocupacao_leitos'],
                                 name='ocupação de leitos de<br>UTI para Covid-19 - média<br>móvel dos últimos 7 dias',
                                 mode='lines+markers', hovertemplate='%{y:.2f}%', customdata=[d], visible=mostrar),
                      secondary_y=True)

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['ocupacao_leitos_ultimo_dia'],
                                 name='ocupação de leitos de<br>UTI para Covid-19<br>no dia anterior',
                                 mode='lines+markers', hovertemplate='%{y:.2f}%', customdata=[d], visible=mostrar),
                      secondary_y=True)

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['leitos_pc'], name='leitos Covid-19 para<br>cada 100 mil habitantes',
                                 mode='lines+markers', customdata=[d], visible=mostrar))

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['internacoes_7d'],
                                 name='internações (UTI e enfermaria,<br>confirmados e suspeitos)<br>média móvel dos últimos 7 dias',
                                 mode='lines+markers', customdata=[d], visible=mostrar))

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['internacoes_7d_l'],
                                 name='internações (UTI e enfermaria,<br>confirmados e suspeitos)<br>média móvel dos 7 dias<br>anteriores',
                                 mode='lines+markers', customdata=[d], visible=mostrar))

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['internacoes_7v7'],
                                 name='variação do número<br>de internações 7 dias',
                                 mode='lines+markers', hovertemplate='%{y:.1f}%', customdata=[d], visible=mostrar),
                      secondary_y=True)

    def cria_lista_opcoes(drs):
        return dict(label=drs,
                    method='update',
                    args=[{'visible': [True if drs in trace['customdata'] else False for trace in fig._data]},
                          {'title.text': titulo_a + drs + titulo_b},
                          {'showlegend': True}])

    fig.update_layout(
        font=dict(family='Roboto'),
        title=titulo_a + 'Estado de São Paulo' + titulo_b,
        xaxis_tickangle=45,
        hovermode='x unified',
        hoverlabel={'namelength': -1},  # para não truncar o nome de cada trace no hover
        template='plotly',
        updatemenus=[go.layout.Updatemenu(active=6,
                                          showactive=True,
                                          buttons=list(s_drs.apply(lambda d: cria_lista_opcoes(d))),
                                          x=0.001, xanchor='left',
                                          y=0.990, yanchor='top')],
        height=600
    )

    fig.update_yaxes(title_text='Número de leitos ou internações', secondary_y=False)
    fig.update_yaxes(title_text='Variação de internações (%)', secondary_y=True)

    # fig.show()

    pio.write_html(fig, file='docs/graficos/drs.html', include_plotlyjs='directory', auto_open=False)

    # versão mobile
    fig.update_traces(mode='lines+text')

    fig.update_xaxes(nticks=10)

    fig.update_layout(
        showlegend=False,
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=10),
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/drs-mobile.html', include_plotlyjs='directory', auto_open=False)


def gera_leitos_municipais(leitos):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['ocupacao_uti_covid_publico'],
                             mode='lines+markers', name='taxa de ocupação de<br>leitos UTI Covid',
                             hovertemplate='%{y:.0f}%'),
                  secondary_y=True)

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['uti_covid_publico'],
                             mode='lines+markers', name='leitos UTI Covid em operação'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['internados_uti_publico'],
                             mode='lines+markers', name='pacientes internados em<br>leitos UTI Covid'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['ventilacao_publico'], visible='legendonly',
                             mode='lines+markers', name='pacientes internados em<br>ventilação mecânica'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['internados_publico'], visible='legendonly',
                             mode='lines+markers', name='total de pacientes internados'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['respiratorio_publico'], visible='legendonly',
                             mode='lines+markers', name='pacientes atendidos com<br>quadro respiratório'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['suspeitos_publico'], visible='legendonly',
                             mode='lines+markers', name='pacientes atendidos com<br>suspeita de Covid-19'))

    d = leitos.dia.size

    frames = [dict(data=[dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.ocupacao_uti_covid_publico[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.uti_covid_publico[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.internados_uti_publico[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.ventilacao_publico[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.internados_publico[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.respiratorio_publico[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.suspeitos_publico[:d + 1])],
                   traces=[0, 1, 2, 3, 4, 5, 6],
                   ) for d in range(0, d)]

    fig.frames = frames

    botoes = [dict(label='Animar', method='animate',
                   args=[None, dict(frame=dict(duration=200, redraw=True), fromcurrent=True, mode='immediate')])]

    fig.update_layout(
        font=dict(family='Roboto'),
        title='Situação dos 20 Hospitais Públicos Municipais' +
              '<br><i>Fonte: <a href = "https://www.prefeitura.sp.gov.br/cidade/' +
              'secretarias/saude/vigilancia_em_saude/doencas_e_agravos/coronavirus/' +
              'index.php?p=295572">Prefeitura de São Paulo</a></i>',
        xaxis_tickangle=45,
        hovermode='x unified',
        hoverlabel={'namelength': -1},  # para não truncar o nome de cada trace no hover
        template='plotly',
        showlegend=True,
        updatemenus=[dict(type='buttons', showactive=False,
                          x=0.05, y=0.95,
                          xanchor='left', yanchor='top',
                          pad=dict(t=0, r=10), buttons=botoes)],
        height=600
    )

    fig.update_yaxes(title_text='Número de pacientes', secondary_y=False)
    fig.update_yaxes(title_text='Taxa de ocupação de UTI (%)', secondary_y=True)

    # fig.show()

    pio.write_html(fig, file='docs/graficos/leitos-municipais.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)

    # versão mobile
    fig.update_traces(mode='lines')

    fig.update_xaxes(nticks=10)

    fig.update_layout(
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=20),
        showlegend=False,
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/leitos-municipais-mobile.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)


def gera_leitos_municipais_privados(leitos):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['ocupacao_uti_covid_privado'],
                             mode='lines+markers', name='taxa de ocupação de<br>leitos UTI Covid',
                             hovertemplate='%{y:.0f}%'),
                  secondary_y=True)

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['uti_covid_privado'],
                             mode='lines+markers', name='leitos UTI Covid em operação'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['internados_uti_privado'],
                             mode='lines+markers', name='pacientes internados em<br>leitos UTI Covid'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['ventilacao_privado'], visible='legendonly',
                             mode='lines+markers', name='pacientes internados em<br>ventilação mecânica'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['internados_privado'], visible='legendonly',
                             mode='lines+markers', name='total de pacientes internados'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['respiratorio_privado'], visible='legendonly',
                             mode='lines+markers', name='pacientes atendidos com<br>quadro respiratório'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['suspeitos_privado'], visible='legendonly',
                             mode='lines+markers', name='pacientes atendidos com<br>suspeita de Covid-19'))

    d = leitos.dia.size

    frames = [dict(data=[dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.ocupacao_uti_covid_privado[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.uti_covid_privado[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.internados_uti_privado[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.ventilacao_privado[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.internados_privado[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.respiratorio_privado[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.suspeitos_privado[:d + 1])],
                   traces=[0, 1, 2, 3, 4, 5, 6],
                   ) for d in range(0, d)]

    fig.frames = frames

    botoes = [dict(label='Animar', method='animate',
                   args=[None, dict(frame=dict(duration=200, redraw=True), fromcurrent=True, mode='immediate')])]

    fig.update_layout(
        font=dict(family='Roboto'),
        title='Situação dos leitos privados contratados pela Prefeitura' +
              '<br><i>Fonte: <a href = "https://www.prefeitura.sp.gov.br/cidade/' +
              'secretarias/saude/vigilancia_em_saude/doencas_e_agravos/coronavirus/' +
              'index.php?p=295572">Prefeitura de São Paulo</a></i>',
        xaxis_tickangle=45,
        hovermode='x unified',
        hoverlabel={'namelength': -1},  # para não truncar o nome de cada trace no hover
        template='plotly',
        showlegend=True,
        updatemenus=[dict(type='buttons', showactive=False,
                          x=0.05, y=0.95,
                          xanchor='left', yanchor='top',
                          pad=dict(t=0, r=10), buttons=botoes)],
        height=600
    )

    fig.update_yaxes(title_text='Número de pacientes', secondary_y=False)
    fig.update_yaxes(title_text='Taxa de ocupação de UTI (%)', secondary_y=True)

    # fig.show()

    pio.write_html(fig, file='docs/graficos/leitos-municipais-privados.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)

    # versão mobile
    fig.update_traces(mode='lines')

    fig.update_xaxes(nticks=10)

    fig.update_layout(
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=20),
        showlegend=False,
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/leitos-municipais-privados-mobile.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)


def gera_leitos_municipais_total(leitos):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['ocupacao_uti_covid_total'],
                             mode='lines+markers', name='taxa de ocupação de<br>leitos UTI Covid',
                             hovertemplate='%{y:.0f}%'),
                  secondary_y=True)

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['uti_covid_total'],
                             mode='lines+markers', name='leitos UTI Covid em operação'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['internados_uti_total'],
                             mode='lines+markers', name='pacientes internados em<br>leitos UTI Covid'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['ventilacao_total'], visible='legendonly',
                             mode='lines+markers', name='pacientes internados em<br>ventilação mecânica'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['internados_total'], visible='legendonly',
                             mode='lines+markers', name='total de pacientes internados'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['respiratorio_total'], visible='legendonly',
                             mode='lines+markers', name='pacientes atendidos com<br>quadro respiratório'))

    fig.add_trace(go.Scatter(x=leitos['dia'], y=leitos['suspeitos_total'], visible='legendonly',
                             mode='lines+markers', name='pacientes atendidos com<br>suspeita de Covid-19'))

    d = leitos.dia.size

    frames = [dict(data=[dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.ocupacao_uti_covid_total[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.uti_covid_total[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.internados_uti_total[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.ventilacao_total[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.internados_total[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.respiratorio_total[:d + 1]),
                         dict(type='scatter', x=leitos.dia[:d + 1], y=leitos.suspeitos_total[:d + 1])],
                   traces=[0, 1, 2, 3, 4, 5, 6],
                   ) for d in range(0, d)]

    fig.frames = frames

    botoes = [dict(label='Animar', method='animate',
                   args=[None, dict(frame=dict(duration=200, redraw=True), fromcurrent=True, mode='immediate')])]

    fig.update_layout(
        font=dict(family='Roboto'),
        title='Situação geral dos leitos públicos e privados' +
              '<br><i>Fonte: <a href = "https://www.prefeitura.sp.gov.br/cidade/' +
              'secretarias/saude/vigilancia_em_saude/doencas_e_agravos/coronavirus/' +
              'index.php?p=295572">Prefeitura de São Paulo</a></i>',
        xaxis_tickangle=45,
        hovermode='x unified',
        hoverlabel={'namelength': -1},  # para não truncar o nome de cada trace no hover
        template='plotly',
        showlegend=True,
        updatemenus=[dict(type='buttons', showactive=False,
                          x=0.05, y=0.95,
                          xanchor='left', yanchor='top',
                          pad=dict(t=0, r=10), buttons=botoes)],
        height=600
    )

    fig.update_yaxes(title_text='Número de pacientes', secondary_y=False)
    fig.update_yaxes(title_text='Taxa de ocupação de UTI (%)', secondary_y=True)

    # fig.show()

    pio.write_html(fig, file='docs/graficos/leitos-municipais-total.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)

    # versão mobile
    fig.update_traces(mode='lines')

    fig.update_xaxes(nticks=10)

    fig.update_layout(
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=20),
        showlegend=False,
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/leitos-municipais-total-mobile.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)


def gera_hospitais_campanha(hospitais_campanha):
    for h in hospitais_campanha.hospital.unique():
        grafico = hospitais_campanha[hospitais_campanha.hospital == h]

        fig = go.Figure()

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['comum'],
                                 mode='lines+markers', name='leitos de enfermaria'))

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['ocupação_comum'],
                                 mode='lines+markers', name='internados em leitos<br>de enfermaria'))

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['uti'],
                                 mode='lines+markers', name='leitos de estabilização'))

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['ocupação_uti'],
                                 mode='lines+markers', name='internados em leitos<br>de estabilização'))

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['altas'],
                                 mode='lines+markers', name='altas', visible='legendonly'))

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['óbitos'],
                                 mode='lines+markers', name='óbitos', visible='legendonly'))

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['transferidos'],
                                 mode='lines+markers', name='transferidos para Hospitais<br>após agravamento clínico',
                                 visible='legendonly'))

        fig.add_trace(go.Scatter(x=grafico['dia'], y=grafico['chegando'],
                                 mode='lines+markers',
                                 name='pacientes em processo de<br>transferência para internação<br>no HMCamp',
                                 visible='legendonly'))

        d = grafico.dia.size

        frames = [dict(data=[dict(type='scatter', x=grafico.dia[:d + 1], y=grafico.comum[:d + 1]),
                             dict(type='scatter', x=grafico.dia[:d + 1], y=grafico.ocupação_comum[:d + 1]),
                             dict(type='scatter', x=grafico.dia[:d + 1], y=grafico.uti[:d + 1]),
                             dict(type='scatter', x=grafico.dia[:d + 1], y=grafico.ocupação_uti[:d + 1]),
                             dict(type='scatter', x=grafico.dia[:d + 1], y=grafico.altas[:d + 1]),
                             dict(type='scatter', x=grafico.dia[:d + 1], y=grafico.óbitos[:d + 1]),
                             dict(type='scatter', x=grafico.dia[:d + 1], y=grafico.transferidos[:d + 1]),
                             dict(type='scatter', x=grafico.dia[:d + 1], y=grafico.chegando[:d + 1])],
                       traces=[0, 1, 2, 3, 4, 5, 6, 7],
                       ) for d in range(0, d)]

        fig.frames = frames

        botoes = [dict(label='Animar', method='animate',
                       args=[None, dict(frame=dict(duration=200, redraw=True), fromcurrent=True, mode='immediate')])]

        fig.update_layout(
            font=dict(family='Roboto'),
            title='Ocupação dos leitos do HMCamp ' + h +
                  '<br><i>Fonte: <a href = "https://www.prefeitura.sp.gov.br/cidade/' +
                  'secretarias/saude/vigilancia_em_saude/doencas_e_agravos/coronavirus/' +
                  'index.php?p=295572">Prefeitura de São Paulo</a></i>',
            xaxis_tickangle=45,
            yaxis_title='Número de leitos ou pacientes',
            hovermode='x unified',
            hoverlabel={'namelength': -1},  # para não truncar o nome de cada trace no hover
            template='plotly',
            updatemenus=[dict(type='buttons', showactive=False,
                              x=0.05, y=0.95,
                              xanchor='left', yanchor='top',
                              pad=dict(t=0, r=10), buttons=botoes)],
            height=600
        )

        # fig.show()

        pio.write_html(fig, file='docs/graficos/' + h.lower() + '.html',
                       include_plotlyjs='directory', auto_open=False, auto_play=False)

        # versão mobile
        fig.update_traces(mode='lines')

        fig.update_xaxes(nticks=10)

        fig.update_layout(
            showlegend=False,
            font=dict(size=11, family='Roboto'),
            margin=dict(l=1, r=1, b=1, t=90, pad=20),
            height=400
        )

        # fig.show()

        pio.write_html(fig, file='docs/graficos/' + h.lower() + '-mobile.html',
                       include_plotlyjs='directory', auto_open=False, auto_play=False)


def gera_evolucao_vacinacao_estado(dados_vacinacao):
    dados = dados_vacinacao.loc[dados_vacinacao.municipio == 'ESTADO DE SAO PAULO'].copy()
    dados['data'] = dados.data.apply(lambda dt: dt.strftime('%d/%b/%y'))
    dados = dados[1:]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(x=dados['data'], y=dados['total_doses'], line=dict(color='green'),
                             mode='lines+markers', name='doses aplicadas'))

    fig.add_trace(go.Bar(x=dados['data'], y=dados['aplicadas_dia'], marker_color='blue',
                         name='doses aplicadas<br>por dia'))

    fig.add_trace(go.Scatter(x=dados['data'], y=dados['perc_vacinadas_1a_dose'], line=dict(color='orange'),
                             mode='lines+markers', name='população vacinada',
                             hovertemplate='%{y:.2f}%'),
                  secondary_y=True)

    d = dados.data.size

    frames = [dict(data=[dict(type='scatter', x=dados.data[:d + 1], y=dados.total_doses[:d + 1]),
                         dict(type='bar', x=dados.data[:d + 1], y=dados.aplicadas_dia[:d + 1]),
                         dict(type='scatter', x=dados.data[:d + 1], y=dados.perc_vacinadas_1a_dose[:d + 1])],
                   traces=[0, 1, 2, 3],
                   ) for d in range(0, d)]

    fig.frames = frames

    botoes = [dict(label='Animar', method='animate',
                   args=[None, dict(frame=dict(duration=200, redraw=True), fromcurrent=True, mode='immediate')])]

    fig.update_layout(
        font=dict(family='Roboto'),
        title='Evolução da vacinação no Estado de São Paulo' +
              '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
              'Governo do Estado de São Paulo</a></i>',
        xaxis_tickangle=45,
        hovermode='x unified',
        hoverlabel={'namelength': -1},  # para não truncar o nome de cada trace no hover
        template='plotly',
        updatemenus=[dict(type='buttons', showactive=False,
                          x=0.05, y=0.95,
                          xanchor='left', yanchor='top',
                          pad=dict(t=0, r=10), buttons=botoes)],
        height=600
    )

    fig.update_yaxes(title_text='Doses aplicadas', secondary_y=False)
    fig.update_yaxes(title_text='População vacinada (%)', secondary_y=True)

    # fig.show()

    pio.write_html(fig, file='docs/graficos/vacinacao-estado.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)

    # versão mobile
    fig.update_traces(selector=dict(type='scatter'), mode='lines')

    fig.update_xaxes(nticks=10)

    fig.update_layout(
        showlegend=False,
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=10),
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/vacinacao-estado-mobile.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)


def gera_evolucao_vacinacao_cidade(dados_vacinacao):
    dados = dados_vacinacao.loc[dados_vacinacao.municipio == 'SAO PAULO'].copy()
    dados['data'] = dados.data.apply(lambda dt: dt.strftime('%d/%b/%y'))
    dados = dados[1:]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(x=dados['data'], y=dados['total_doses'], line=dict(color='green'),
                             mode='lines+markers', name='doses aplicadas'))

    fig.add_trace(go.Bar(x=dados['data'], y=dados['aplicadas_dia'], marker_color='blue',
                         name='doses aplicadas<br>por dia'))

    fig.add_trace(go.Scatter(x=dados['data'], y=dados['perc_vacinadas_1a_dose'], line=dict(color='orange'),
                             mode='lines+markers', name='população vacinada',
                             hovertemplate='%{y:.2f}%'),
                  secondary_y=True)

    d = dados.data.size

    frames = [dict(data=[dict(type='scatter', x=dados.data[:d + 1], y=dados.total_doses[:d + 1]),
                         dict(type='bar', x=dados.data[:d + 1], y=dados.aplicadas_dia[:d + 1]),
                         dict(type='scatter', x=dados.data[:d + 1], y=dados.perc_vacinadas_1a_dose[:d + 1])],
                   traces=[0, 1, 2, 3],
                   ) for d in range(0, d)]

    fig.frames = frames

    botoes = [dict(label='Animar', method='animate',
                   args=[None, dict(frame=dict(duration=200, redraw=True), fromcurrent=True, mode='immediate')])]

    fig.update_layout(
        font=dict(family='Roboto'),
        title='Evolução da vacinação na cidade de São Paulo' +
              '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
              'Governo do Estado de São Paulo</a></i>',
        xaxis_tickangle=45,
        hovermode='x unified',
        hoverlabel={'namelength': -1},  # para não truncar o nome de cada trace no hover
        template='plotly',
        updatemenus=[dict(type='buttons', showactive=False,
                          x=0.05, y=0.95,
                          xanchor='left', yanchor='top',
                          pad=dict(t=0, r=10), buttons=botoes)],
        height=600
    )

    fig.update_yaxes(title_text='Doses aplicadas', secondary_y=False)
    fig.update_yaxes(title_text='População vacinada (%)', secondary_y=True)

    # fig.show()

    pio.write_html(fig, file='docs/graficos/vacinacao-cidade.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)

    # versão mobile
    fig.update_traces(selector=dict(type='scatter'), mode='lines')

    fig.update_xaxes(nticks=10)

    fig.update_layout(
        showlegend=False,
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=10),
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/vacinacao-cidade-mobile.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)


def gera_populacao_vacinada(dados):
    filtro_data = dados.data == dados.data.max()
    filtro_estado = dados.municipio == 'ESTADO DE SAO PAULO'
    filtro_cidade = dados.municipio == 'SAO PAULO'

    dados_estado = dados.loc[filtro_data & filtro_estado].copy()
    dados_estado.loc[:, 'data'] = dados_estado.data.apply(lambda dt: dt.strftime('%d/%b/%y'))

    dados_cidade = dados.loc[filtro_data & filtro_cidade].copy()
    dados_cidade.loc[:, 'data'] = dados_cidade.data.apply(lambda dt: dt.strftime('%d/%b/%y'))

    rotulos = ['população vacinada', 'população aguardando vacinação']
    pizza_estado = [dados_estado['1a_dose'].item(), dados_estado['populacao'].item() - dados_estado['1a_dose'].item()]
    pizza_cidade = [dados_cidade['1a_dose'].item(), dados_cidade['populacao'].item() - dados_cidade['1a_dose'].item()]

    fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'domain'}, {'type': 'domain'}]])

    fig.add_trace(go.Pie(labels=rotulos, values=pizza_estado, name='Estado',
                         marker=dict(colors=['green', 'red'])), 1, 1)
    fig.add_trace(go.Pie(labels=rotulos, values=pizza_cidade, name='Cidade',
                         marker=dict(colors=['green', 'red'])), 1, 2)

    fig.update_traces(hole=.4, hoverinfo="label+percent+name+value")

    fig.update_layout(
        title='População vacinada no estado e na cidade de São Paulo'
              '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
              'Governo do Estado de São Paulo</a></i>',
        font=dict(family='Roboto'),
        annotations=[dict(text='Estado de SP', x=0.17, y=0.5, font=dict(size=15, family='Roboto'), showarrow=False),
                     dict(text='Cidade de SP', x=0.80, y=0.5, font=dict(size=15, family='Roboto'), showarrow=False)],
        height=600
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/populacao-vacinada.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)

    # versão mobile
    fig.update_layout(
        showlegend=False,
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=10),
        annotations=[dict(text='Estado', x=0.17, y=0.5, font=dict(size=9, family='Roboto'), showarrow=False),
                     dict(text='Cidade', x=0.85, y=0.5, font=dict(size=9, family='Roboto'), showarrow=False)],
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/populacao-vacinada-mobile.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)


def gera_tipo_doses(dados):
    filtro_data = dados.data == dados.data.max()
    filtro_estado = dados.municipio == 'ESTADO DE SAO PAULO'
    filtro_cidade = dados.municipio == 'SAO PAULO'

    dados_estado = dados.loc[filtro_data & filtro_estado].copy()
    dados_estado.loc[:, 'data'] = dados_estado.data.apply(lambda dt: dt.strftime('%d/%b/%y'))

    dados_cidade = dados.loc[filtro_data & filtro_cidade].copy()
    dados_cidade.loc[:, 'data'] = dados_cidade.data.apply(lambda dt: dt.strftime('%d/%b/%y'))

    rotulos = ['1ª dose', '2ª dose']
    pizza_estado = [dados_estado['1a_dose'].item(), dados_estado['2a_dose'].item()]
    pizza_cidade = [dados_cidade['1a_dose'].item(), dados_cidade['2a_dose'].item()]

    fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'domain'}, {'type': 'domain'}]])

    fig.add_trace(go.Pie(labels=rotulos, values=pizza_estado, name='Estado',
                         marker=dict(colors=['green', 'blue'])), 1, 1)
    fig.add_trace(go.Pie(labels=rotulos, values=pizza_cidade, name='Cidade',
                         marker=dict(colors=['green', 'blue'])), 1, 2)

    fig.update_traces(hole=.4, hoverinfo="label+percent+name+value")

    fig.update_layout(
        title='1ª e 2ª doses aplicadas pelo estado e pela cidade de São Paulo'
              '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
              'Governo do Estado de São Paulo</a></i>',
        font=dict(family='Roboto'),
        annotations=[dict(text='Estado de SP', x=0.17, y=0.5, font=dict(size=15, family='Roboto'), showarrow=False),
                     dict(text='Cidade de SP', x=0.80, y=0.5, font=dict(size=15, family='Roboto'), showarrow=False)],
        height=600
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/vacinas-tipo.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)

    # versão mobile
    fig.update_layout(
        showlegend=False,
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=10),
        annotations=[dict(text='Estado', x=0.17, y=0.5, font=dict(size=9, family='Roboto'), showarrow=False),
                     dict(text='Cidade', x=0.85, y=0.5, font=dict(size=9, family='Roboto'), showarrow=False)],
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/vacinas-tipo-mobile.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)


def gera_doses_aplicadas(dados):
    filtro_data = dados.data == dados.data.max()
    filtro_estado = dados.municipio == 'ESTADO DE SAO PAULO'
    filtro_cidade = dados.municipio == 'SAO PAULO'

    dados_estado = dados.loc[filtro_data & filtro_estado].copy()
    dados_estado.loc[:, 'data'] = dados_estado.data.apply(lambda dt: dt.strftime('%d/%b/%y'))

    dados_cidade = dados.loc[filtro_data & filtro_cidade].copy()
    dados_cidade.loc[:, 'data'] = dados_cidade.data.apply(lambda dt: dt.strftime('%d/%b/%y'))

    rotulos = ['doses aplicadas', 'doses disponíveis para aplicação']
    pizza_estado = [dados_estado['total_doses'].item(), dados_estado['doses_recebidas'].item() - dados_estado['total_doses'].item()]
    pizza_cidade = [dados_cidade['total_doses'].item(), dados_cidade['doses_recebidas'].item() - dados_cidade['total_doses'].item()]

    fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'domain'}, {'type': 'domain'}]])

    fig.add_trace(go.Pie(labels=rotulos, values=pizza_estado, name='Estado',
                         marker=dict(colors=['green', 'red'])), 1, 1)
    fig.add_trace(go.Pie(labels=rotulos, values=pizza_cidade, name='Cidade',
                         marker=dict(colors=['green', 'red'])), 1, 2)

    fig.update_traces(hole=.4, hoverinfo="label+percent+name+value")

    fig.update_layout(
        title='Vacinas disponíveis x aplicadas pelo estado e pela cidade de São Paulo'
              '<br><i>Fonte: <a href = "https://www.seade.gov.br/coronavirus/">' +
              'Governo do Estado de São Paulo</a></i>',
        font=dict(family='Roboto'),
        annotations=[dict(text='Estado de SP', x=0.17, y=0.5, font=dict(size=15, family='Roboto'), showarrow=False),
                     dict(text='Cidade de SP', x=0.80, y=0.5, font=dict(size=15, family='Roboto'), showarrow=False)],
        height=600
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/vacinas-aplicadas.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)

    # versão mobile
    fig.update_layout(
        showlegend=False,
        font=dict(size=11, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=90, pad=10),
        annotations=[dict(text='Estado', x=0.17, y=0.5, font=dict(size=9, family='Roboto'), showarrow=False),
                     dict(text='Cidade', x=0.85, y=0.5, font=dict(size=9, family='Roboto'), showarrow=False)],
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/vacinas-aplicadas-mobile.html',
                   include_plotlyjs='directory', auto_open=False, auto_play=False)


def gera_tabela_vacinacao(dados):
    dados_tab = dados.loc[dados.data == dados.data.max()].copy()
    dados_tab.columns = ['Data', 'Município', '1ª dose', '2ª dose', 'Aplicadas no dia', 'Doses aplicadas',
                         'Doses recebidas', 'Aplicadas (%)', '1ª dose (%)', '2ª dose (%)', 'População']

    dados_tab.drop(columns='Aplicadas no dia', inplace=True)

    dados_tab['Município'] = dados_tab['Município'].apply(lambda m: formata_municipio(m))
    dados_tab['1ª dose'] = dados_tab['1ª dose'].apply(lambda x: f'{x:8,.0f}'.replace(',', '.'))
    dados_tab['1ª dose (%)'] = dados_tab['1ª dose (%)'].apply(lambda x: f'{x:8.2f}%'.replace('.', ','))
    dados_tab['2ª dose'] = dados_tab['2ª dose'].apply(lambda x: f'{x:8,.0f}'.replace(',', '.'))
    dados_tab['2ª dose (%)'] = dados_tab['2ª dose (%)'].apply(lambda x: f'{x:8.2f}%'.replace('.', ','))
    dados_tab['Doses aplicadas'] = dados_tab['Doses aplicadas'].apply(lambda x: f'{x:8,.0f}'.replace(',', '.'))
    dados_tab['Doses recebidas'] = dados_tab['Doses recebidas'].apply(lambda x: f'{x:8,.0f}'.replace(',', '.'))
    dados_tab['Aplicadas (%)'] = dados_tab['Aplicadas (%)'].apply(lambda x: f'{x:8.2f}%'.replace('.', ','))
    dados_tab['População'] = dados_tab['População'].apply(lambda x: f'{x:8,.0f}'.replace(',', '.'))

    cabecalho = ['<b>Município</b>', '<b>1ª dose</b>', '<b>1ª dose (%)</b>', '<b>2ª dose</b>',
                 '<b>2ª dose (%)</b>', '<b>Doses aplicadas</b>', '<b>Doses recebidas</b>',
                 '<b>Aplicadas (%)</b>', '<b>População</b>']

    valores = [dados_tab['Município'], dados_tab['1ª dose'], dados_tab['1ª dose (%)'],
               dados_tab['2ª dose'], dados_tab['2ª dose (%)'],
               dados_tab['Doses aplicadas'], dados_tab['Doses recebidas'], dados_tab['Aplicadas (%)'],
               dados_tab['População']]

    fig = go.Figure(data=[go.Table(header=dict(values=cabecalho,
                                               fill_color='#00aabb',
                                               font=dict(color='white'),
                                               align='right',
                                               line=dict(width=5)),
                                   cells=dict(values=valores,
                                              fill_color='lavender',
                                              align='right',
                                              line=dict(width=5),
                                              height=30),
                                   columnwidth=[1, 1, 1, 1, 1, 1, 1, 1, 1])])

    atualizado_em = dados.data.max().strftime('%d/%m/%y')

    fig.update_layout(
        font=dict(size=15, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=30, pad=5),
        annotations=[dict(x=0, y=1.05, showarrow=False, font=dict(size=13),
                          text=f'Dados de {atualizado_em} | <i><b>Fonte:</b> <a href = '
                               f'"https://www.saopaulo.sp.gov.br/coronavirus">'
                               f'Governo do Estado de São Paulo</a></i>')],
        height=600
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/tabela-vacinacao.html', include_plotlyjs='directory', auto_open=False)

    cabecalho = ['<b>Município</b>', '<b>População vacinada (%)</b>']

    fig = go.Figure(data=[go.Table(header=dict(values=cabecalho,
                                               fill_color='#00aabb',
                                               font=dict(color='white'),
                                               align='right',
                                               line=dict(width=5)),
                                   cells=dict(values=[dados_tab['Município'], dados_tab['1ª dose (%)']],
                                              fill_color='lavender',
                                              align='right',
                                              line=dict(width=5),
                                              height=30),
                                   columnwidth=[1, 1, 1, 1, 1, 1, 1, 1, 1])])

    fig.update_layout(
        font=dict(size=13, family='Roboto'),
        margin=dict(l=1, r=1, b=1, t=30, pad=5),
        annotations=[dict(x=0, y=1.05, showarrow=False, font=dict(size=13, family='Roboto'),
                          text=f'Dados de {atualizado_em} | <i><b>Fonte:</b> <a href = '
                               f'"https://www.saopaulo.sp.gov.br/coronavirus">'
                               f'Governo do Estado de São Paulo</a></i>')],
        height=400
    )

    # fig.show()

    pio.write_html(fig, file='docs/graficos/tabela-vacinacao-mobile.html', include_plotlyjs='directory',
                   auto_open=False)


def atualiza_service_worker(dados_estado):
    data_anterior = dados_estado.data.iat[-2].strftime('%d/%m/%Y')
    data_atual = dados_estado.data.iat[-1].strftime('%d/%m/%Y')

    with open('docs/serviceWorker.js', 'r') as file:
        filedata = file.read()

    versao_anterior = int(filedata[16:18])

    # primeira atualização no dia
    if filedata.count(data_atual) == 0:
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
    data_processamento_cidade = datetime.now()
    data_processamento_estado = datetime.now()

    main()
