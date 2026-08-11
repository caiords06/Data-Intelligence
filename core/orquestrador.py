"""Orquestração do pipeline de análise de dados.

Este módulo concentra o fluxo de negócio e não depende de Tkinter. A interface
apenas fornece configurações/caminhos e consome o resultado final.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from copy import deepcopy

import pandas as pd

from analysis.temporal import analisar_periodos
from dados.classificador import classificar_dataframe, obter_indicadores_sugeridos
from dados.estrutural import analisar_estrutura
from dados.indicadores import calcular_indicadores
from dados.leitor import (
    carregar_multiplas_planilhas,
    consolidar_planilhas,
    verificar_compatibilidade,
)
from dados.qualidade import analisar_qualidade
from dados.tratamento import tratar_dataframe

Logger = Callable[[str], None]
ProgressCallback = Callable[[int, str], None]
CancelCallback = Callable[[], bool]


class ProcessamentoCancelado(RuntimeError):
    """Interrupção cooperativa do pipeline analítico."""

MODULOS_PADRAO = {
    "tratamento": True,
    "estrutural": True,
    "indicadores": True,
    "temporal": True,
    "qualidade": True,
}


def normalizar_configuracao(configuracao: dict | None) -> dict:
    configuracao = dict(configuracao or {})
    modulos_recebidos = configuracao.get("modulos") or {}
    configuracao["modulos"] = {
        nome: bool(modulos_recebidos.get(nome, padrao))
        for nome, padrao in MODULOS_PADRAO.items()
    }
    configuracao.setdefault("fonte", "computador")
    configuracao.setdefault("categoria", "automatica")
    configuracao.setdefault("periodo", "automatico")
    configuracao.setdefault("ia", False)
    configuracao.setdefault("arquivos", [])
    return configuracao


class OrquestradorAnalise:
    def __init__(
        self,
        logger: Logger | None = None,
        progresso: ProgressCallback | None = None,
        cancelar: CancelCallback | None = None,
    ) -> None:
        self._logger = logger or (lambda _mensagem: None)
        self._progresso = progresso or (lambda _valor, _mensagem: None)
        self._cancelar = cancelar or (lambda: False)

    def log(self, mensagem: str = "") -> None:
        self._logger(str(mensagem))

    def progresso(self, valor: int, mensagem: str) -> None:
        if self._cancelar():
            raise ProcessamentoCancelado("Processamento cancelado com segurança.")
        self._progresso(max(0, min(100, int(valor))), mensagem)

    def separador(self, caractere: str = "=") -> None:
        self.log(caractere * 40)

    def processar(
        self,
        caminhos: Iterable[str],
        configuracao: dict | None = None,
    ) -> dict:
        config = normalizar_configuracao(configuracao)
        caminhos = list(dict.fromkeys(str(caminho) for caminho in caminhos if caminho))
        if not caminhos:
            raise ValueError("Nenhum arquivo foi selecionado para análise.")

        fonte = str(config.get("fonte", "computador")).lower()
        fontes_preparadas = {
            "computador",
            "google_drive",
            "onedrive",
            "banco_de_dados",
            "url",
        }
        if fonte not in fontes_preparadas:
            raise ValueError(f"Fonte de dados não suportada: {fonte}.")

        if config.get("ia"):
            self.log(
                "[INFO] IA foi solicitada, mas a integração de IA ainda não "
                "faz parte do pipeline desta versão. O motor local seguirá normalmente."
            )

        self.progresso(5, "Carregando arquivos...")
        self.separador()
        self.log("MÚLTIPLOS ARQUIVOS SELECIONADOS")
        self.separador()
        self.log(f"[OK] Arquivos selecionados: {len(caminhos)}")
        for indice, caminho in enumerate(caminhos, start=1):
            self.log(f"[{indice}] {caminho}")

        resultados_arquivos = carregar_multiplas_planilhas(caminhos)
        self.separador()
        self.log("ARQUIVOS CARREGADOS")
        self.separador()
        for item in resultados_arquivos:
            df_item = item["dataframe"]
            self.log(f"[OK] {item['nome_arquivo']}")
            self.log(f"    Registros: {len(df_item)}")
            self.log(f"    Colunas: {len(df_item.columns)}")
            self._registrar_periodo(item.get("periodo") or {})

        self.progresso(20, "Verificando compatibilidade...")
        compatibilidade = verificar_compatibilidade(resultados_arquivos)
        if not compatibilidade["compativel"]:
            self.log("[ERRO] Os arquivos possuem estruturas diferentes.")
            for item in compatibilidade["incompatibilidades"]:
                self.log(f"[ERRO] Arquivo: {item['arquivo']}")
                if item.get("faltando"):
                    self.log(f"       Colunas ausentes: {item['faltando']}")
                if item.get("extras"):
                    self.log(f"       Colunas extras: {item['extras']}")
                if item.get("tipos"):
                    self.log(f"       Tipos incompatíveis: {item['tipos']}")
            raise ValueError("Os arquivos selecionados possuem estruturas incompatíveis.")
        self.log("[OK] Estrutura dos arquivos compatível.")

        self.progresso(30, "Consolidando arquivos...")
        df_consolidado = consolidar_planilhas(resultados_arquivos)
        self.separador()
        self.log("CONSOLIDAÇÃO CONCLUÍDA")
        self.separador()
        self.log(f"[OK] Arquivos consolidados: {len(caminhos)}")
        self.log(f"[OK] Total de registros: {len(df_consolidado)}")
        self.log(f"[OK] Total de colunas: {len(df_consolidado.columns)}")

        return self._analisar_dataframe_consolidado(
            df_consolidado,
            config,
            caminhos=caminhos,
            resultados_arquivos=resultados_arquivos,
        )

    def processar_dataframe(
        self,
        dataframe: pd.DataFrame,
        configuracao: dict | None = None,
        *,
        nome_fonte: str = "Módulo empresarial",
    ) -> dict:
        """Executa o mesmo motor sobre dados internos, sem arquivo temporário."""
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("A fonte empresarial precisa ser um pandas.DataFrame.")
        if dataframe.empty:
            raise ValueError("O módulo ainda não possui registros para análise.")
        config = normalizar_configuracao(configuracao)
        config["fonte"] = "sistema"
        self.progresso(10, "Carregando dados do módulo...")
        self.separador()
        self.log("FONTE EMPRESARIAL SELECIONADA")
        self.separador()
        self.log(f"[OK] Fonte: {nome_fonte}")
        self.log(f"[OK] Registros: {len(dataframe)}")
        self.log(f"[OK] Colunas: {len(dataframe.columns)}")
        return self._analisar_dataframe_consolidado(
            dataframe.copy(deep=True),
            config,
            caminhos=[nome_fonte],
            resultados_arquivos=[
                {
                    "nome_arquivo": nome_fonte,
                    "dataframe": dataframe.copy(deep=True),
                    "periodo": {},
                }
            ],
        )

    def _analisar_dataframe_consolidado(
        self,
        dataframe: pd.DataFrame,
        config: dict,
        *,
        caminhos: list[str],
        resultados_arquivos: list[dict],
    ) -> dict:
        df_original = dataframe.copy(deep=True)
        df_consolidado = dataframe.copy(deep=True)
        df_consolidado, relatorio_tratamento = self._executar_tratamento(
            df_consolidado,
            config,
        )
        analise_estrutural = self._executar_estrutural(df_consolidado, config)
        analise_qualidade = self._executar_qualidade(
            df_consolidado,
            config,
            relatorio_tratamento,
        )
        classificacao = self._executar_classificacao(df_consolidado, config)
        indicadores = self._executar_indicadores(df_consolidado, classificacao, config)
        analise_temporal = self._executar_temporal(df_consolidado, classificacao, config)

        resultado = {
            "arquivos": caminhos,
            "configuracao": deepcopy(config),
            "resultados_arquivos": resultados_arquivos,
            "dataframe_original": df_original,
            "dataframe": df_consolidado,
            "tratamento": relatorio_tratamento,
            "categoria": classificacao["categoria"],
            "classificacao": classificacao,
            "estrutural": analise_estrutural,
            "qualidade": analise_qualidade,
            "indicadores": indicadores or None,
            "temporal": analise_temporal,
        }

        self.separador()
        self.log("RESULTADO ANALÍTICO CONSOLIDADO")
        self.separador()
        self.log(f"[OK] Categoria: {resultado['categoria'].upper()}")
        self.log(
            f"[OK] Tratamento: "
            f"{'Disponível' if relatorio_tratamento else 'Não executado'}"
        )
        self.log(f"[OK] Estrutural: {'Disponível' if analise_estrutural else 'Não executada'}")
        self.log(f"[OK] Qualidade: {'Disponível' if analise_qualidade else 'Não executada'}")
        self.log(f"[OK] Indicadores: {'Disponível' if indicadores else 'Não executados'}")
        self.log(f"[OK] Temporal: {'Disponível' if analise_temporal else 'Não executada'}")
        self.log("[OK] Análise concluída.")
        self.progresso(100, "Análise concluída com sucesso.")
        return resultado

    def _registrar_periodo(self, periodo: dict) -> None:
        origem = periodo.get("origem_identificacao")
        if origem == "coluna_data":
            self.log("    [PERÍODO] Identificado pela coluna de data.")
        elif origem == "nome_arquivo":
            self.log("    [PERÍODO] Identificado pelo nome do arquivo.")
        else:
            self.log("    [AVISO] Período não identificado.")
            return

        self.log(f"    [PERÍODO] {periodo.get('periodo')}")
        if periodo.get("trimestre"):
            self.log(f"    [TRIMESTRE] {periodo.get('trimestre')}")
        if periodo.get("semestre"):
            self.log(f"    [SEMESTRE] {periodo.get('semestre')}")

    def _executar_tratamento(
        self,
        df: pd.DataFrame,
        config: dict,
    ) -> tuple[pd.DataFrame, dict | None]:
        if not config["modulos"]["tratamento"]:
            self.log("[INFO] Tratamento seguro dos dados desativado na configuração.")
            return df.copy(), None

        self.progresso(36, "Tratando e validando dados...")
        self.separador()
        self.log("TRATAMENTO E VALIDAÇÃO")
        self.separador()
        tratado, relatorio = tratar_dataframe(df)
        self.log(
            f"[OK] Colunas normalizadas: "
            f"{relatorio['quantidade_colunas_renomeadas']}"
        )
        self.log(f"[OK] Textos ajustados: {relatorio['textos_ajustados']}")
        self.log(
            f"[OK] Colunas convertidas: "
            f"{relatorio['quantidade_colunas_convertidas']}"
        )
        self.log(
            f"[{'AVISO' if relatorio['total_valores_invalidos'] else 'OK'}] "
            f"Valores inválidos encontrados: {relatorio['total_valores_invalidos']}"
        )
        if relatorio["colisoes_colunas"]:
            self.log(
                f"[AVISO] Colisões de nomes resolvidas: "
                f"{relatorio['quantidade_colisoes_colunas']}"
            )
        self.log("[OK] Nenhuma linha foi removida automaticamente.")
        return tratado, relatorio

    def _executar_estrutural(self, df: pd.DataFrame, config: dict) -> dict | None:
        if not config["modulos"]["estrutural"]:
            self.log("[INFO] Análise estrutural desativada na configuração.")
            return None

        self.progresso(42, "Analisando estrutura da base...")
        self.separador()
        self.log("ANÁLISE ESTRUTURAL")
        self.separador()
        estrutura = analisar_estrutura(df)
        self.log(f"[OK] Registros: {estrutura['total_registros']:,}")
        self.log(f"[OK] Colunas: {estrutura['total_colunas']}")
        self.log(f"[+] Colunas numéricas: {estrutura['quantidade_numericas']}")
        self.log(f"[+] Colunas textuais: {estrutura['quantidade_textuais']}")
        self.log(f"[+] Colunas temporais: {estrutura['quantidade_temporais']}")
        self.log("[OK] Análise estrutural concluída.")
        return estrutura

    def _executar_qualidade(
        self,
        df: pd.DataFrame,
        config: dict,
        relatorio_tratamento: dict | None,
    ) -> dict | None:
        if not config["modulos"]["qualidade"]:
            self.log("[INFO] Qualidade dos dados desativada na configuração.")
            return None

        self.progresso(54, "Analisando qualidade dos dados...")
        self.separador()
        self.log("QUALIDADE DOS DADOS")
        self.separador()
        qualidade = analisar_qualidade(
            df,
            relatorio_tratamento=relatorio_tratamento,
        )
        self.log(f"[+] Completude: {qualidade['completude']:.2f}%")
        self.log(f"[+] Valores ausentes: {qualidade['valores_ausentes']}")
        self.log(f"[+] Linhas com dados ausentes: {qualidade['linhas_com_ausentes']}")
        self.log(f"[+] Registros duplicados: {qualidade['linhas_duplicadas']}")
        self.log(f"[+] Colunas totalmente vazias: {qualidade['quantidade_colunas_vazias']}")
        self.log(f"[+] Validade dos tipos: {qualidade['validade']:.2f}%")
        self.log(f"[+] Consistência: {qualidade['consistencia']:.2f}%")
        self.log(
            f"[+] Inconsistências: "
            f"{qualidade['inconsistencias']['total_inconsistencias']}"
        )
        self.log(f"[+] Outliers sinalizados: {qualidade['outliers']['total_outliers']}")
        self.log("-" * 40)
        self.log(f"[OK] Score de qualidade: {qualidade['score_qualidade']:.2f}/100")
        self.log(f"[OK] Classificação: {qualidade['nivel_qualidade']}")

        if qualidade["ausentes_por_coluna"]:
            self.log("-" * 40)
            self.log("COLUNAS COM DADOS AUSENTES")
            self.log("-" * 40)
            for coluna, quantidade in qualidade["ausentes_por_coluna"].items():
                self.log(f"[!] {coluna}: {quantidade}")

        self.log("[OK] Análise de qualidade concluída.")
        return qualidade

    def _executar_classificacao(self, df: pd.DataFrame, config: dict) -> dict:
        self.progresso(66, "Classificando base...")
        self.separador()
        self.log("CLASSIFICAÇÃO DA BASE")
        self.separador()

        classificacao = classificar_dataframe(df)
        categoria_detectada = classificacao["categoria"]
        confianca_detectada = classificacao["confianca"]
        categoria_solicitada = str(config.get("categoria", "automatica"))

        classificacao["categoria_detectada"] = categoria_detectada
        classificacao["confianca_detectada"] = confianca_detectada

        if categoria_solicitada != "automatica":
            classificacao["categoria"] = categoria_solicitada
            classificacao["origem_categoria"] = "usuario"
            classificacao["indicadores_sugeridos"] = obter_indicadores_sugeridos(
                categoria_solicitada
            )
            self.log(f"[OK] Categoria definida pelo usuário: {categoria_solicitada.upper()}")
            self.log(
                f"[INFO] Detecção automática original: {categoria_detectada.upper()} "
                f"({confianca_detectada}%)"
            )
        else:
            classificacao["origem_categoria"] = "automatica"
            self.log(f"[OK] Categoria provável: {categoria_detectada.upper()}")
            self.log(f"[OK] Confiança: {confianca_detectada}%")

        self.log("-" * 40)
        self.log("CAMPOS IDENTIFICADOS")
        self.log("-" * 40)
        for coluna, informacao in classificacao["campos"].items():
            campo = informacao["campo"]
            tipo = informacao["tipo"]
            if campo:
                self.log(f"[OK] {coluna} → {campo} ({tipo})")
            else:
                self.log(f"[INFO] {coluna} → não identificado ({tipo})")

        self.log("-" * 40)
        self.log("INDICADORES SUGERIDOS")
        self.log("-" * 40)
        sugeridos = classificacao.get("indicadores_sugeridos") or []
        if sugeridos:
            for indicador in sugeridos:
                self.log(f"[+] {indicador}")
        else:
            self.log("[INFO] Nenhum indicador específico sugerido para esta categoria.")

        self.log("[OK] Classificação concluída.")
        return classificacao

    def _executar_indicadores(
        self,
        df: pd.DataFrame,
        classificacao: dict,
        config: dict,
    ) -> dict:
        if not config["modulos"]["indicadores"]:
            self.log("[INFO] Módulo de indicadores desativado na configuração.")
            return {}

        categoria = classificacao["categoria"]
        self.progresso(78, "Calculando indicadores...")
        indicadores = calcular_indicadores(categoria, df, classificacao["campos"])
        if not indicadores:
            self.log(
                f"[INFO] Não existe motor específico de indicadores para a categoria '{categoria}'."
            )
            return {}

        self.separador()
        self.log("MOTOR DE INDICADORES")
        self.separador()
        self.log("[OK] Indicadores calculados.")
        self._registrar_indicadores(categoria, indicadores)
        return indicadores

    def _registrar_indicadores(self, categoria: str, indicadores: dict) -> None:
        self.separador()
        self.log(f"RESUMO {categoria.replace('_', ' ').upper()}")
        self.separador()

        universais = indicadores.get("universais") or {}
        self.log(f"[+] Registros analisados: {universais.get('total_registros', 0):,}")
        self.log(f"[+] Colunas de negócio: {universais.get('total_colunas', 0)}")
        self.log(f"[+] Completude universal: {universais.get('completude', 0):.2f}%")

        campos_por_categoria = {
            "vendas": (
                ("faturamento_total", "Faturamento total", "moeda"),
                ("total_vendas", "Total de vendas", "inteiro"),
                ("quantidade_total", "Quantidade vendida", "inteiro"),
                ("ticket_medio", "Ticket médio", "moeda"),
            ),
            "financeiro": (
                ("receita_total", "Receita total", "moeda"),
                ("despesa_total", "Despesa total", "moeda"),
                ("saldo", "Saldo", "moeda"),
                ("margem_operacional", "Margem operacional", "percentual"),
            ),
            "estoque": (
                ("estoque_total", "Estoque total", "numero"),
                ("produtos_distintos", "Produtos distintos", "inteiro"),
                ("produtos_baixo_estoque", "Baixo estoque", "inteiro"),
                ("valor_estoque", "Valor do estoque", "moeda"),
            ),
            "cadastro": (
                ("total_registros", "Registros", "inteiro"),
                ("registros_unicos", "Registros únicos", "inteiro"),
                ("registros_duplicados", "Duplicados", "inteiro"),
                ("completude", "Completude", "percentual"),
            ),
            "recursos_humanos": (
                ("total_colaboradores", "Colaboradores", "inteiro"),
                ("colaboradores_ativos", "Ativos", "inteiro"),
                ("folha_total", "Folha total", "moeda"),
                ("turnover_percentual", "Turnover", "percentual"),
            ),
            "compras": (
                ("total_solicitacoes", "Solicitações", "inteiro"),
                ("solicitacoes_pendentes", "Pendentes", "inteiro"),
                ("valor_solicitado", "Valor solicitado", "moeda"),
                ("taxa_aprovacao", "Taxa de aprovação", "percentual"),
            ),
            "ti": (
                ("total_chamados", "Chamados", "inteiro"),
                ("chamados_abertos", "Abertos", "inteiro"),
                ("chamados_criticos", "Críticos", "inteiro"),
                ("taxa_resolucao", "Taxa de resolução", "percentual"),
            ),
            "marketing": (
                ("investimento_total", "Investimento", "moeda"),
                ("receita_atribuida", "Receita atribuída", "moeda"),
                ("roas", "ROAS", "numero"),
                ("taxa_conversao", "Taxa de conversão", "percentual"),
            ),
            "administrativo": (
                ("total_solicitacoes", "Solicitações", "inteiro"),
                ("solicitacoes_pendentes", "Pendentes", "inteiro"),
                ("valor_total", "Valor total", "moeda"),
                ("taxa_aprovacao", "Taxa de aprovação", "percentual"),
            ),
            "juridico": (
                ("total_contratos", "Contratos", "inteiro"),
                ("contratos_vencendo_30_dias", "Vencendo em 30 dias", "inteiro"),
                ("valor_em_risco", "Valor em risco", "moeda"),
                ("contratos_alto_risco", "Alto risco", "inteiro"),
            ),
            "comercial": (
                ("total_oportunidades", "Oportunidades", "inteiro"),
                ("oportunidades_abertas", "Abertas", "inteiro"),
                ("pipeline_aberto", "Pipeline", "moeda"),
                ("taxa_conversao", "Taxa de conversão", "percentual"),
            ),
        }
        campos = campos_por_categoria.get(categoria, ())
        for chave, rotulo, tipo in campos:
            if chave not in indicadores:
                continue
            valor = indicadores[chave]
            if tipo == "moeda":
                self.log(f"[+] {rotulo}: R$ {valor:,.2f}")
            elif tipo == "percentual":
                self.log(f"[+] {rotulo}: {valor:,.2f}%")
            elif tipo == "inteiro":
                self.log(f"[+] {rotulo}: {valor:,.0f}")
            else:
                self.log(f"[+] {rotulo}: {valor:,.2f}")

        self.log("-" * 40)
        self.log("DESTAQUES")
        self.log("-" * 40)
        if "produto_maior_faturamento" in indicadores:
            self.log(f"[+] Produto líder: {indicadores['produto_maior_faturamento']}")
            self.log(f"    Faturamento: R$ {indicadores['valor_produto_lider']:,.2f}")
        if "loja_maior_faturamento" in indicadores:
            self.log(f"[+] Loja líder: {indicadores['loja_maior_faturamento']}")
            self.log(f"    Faturamento: R$ {indicadores['valor_loja_lider']:,.2f}")
        destaques = {
            "financeiro": (
                ("categoria_maior_movimentacao", "Categoria de maior movimentação"),
            ),
            "estoque": (
                ("produto_critico", "Produto crítico"),
                ("produto_maior_estoque", "Maior estoque"),
            ),
            "cadastro": (("maior_categoria", "Maior categoria"),),
            "recursos_humanos": (("maior_setor", "Maior setor"),),
        }
        for chave, rotulo in destaques.get(categoria, ()):
            if indicadores.get(chave) is not None:
                self.log(f"[+] {rotulo}: {indicadores[chave]}")

    def _executar_temporal(
        self,
        df: pd.DataFrame,
        classificacao: dict,
        config: dict,
    ) -> dict | None:
        if not config["modulos"]["temporal"]:
            self.log("[INFO] Análise temporal desativada na configuração.")
            return None

        self.progresso(90, "Executando análise temporal...")
        self.separador()
        self.log("ANÁLISE TEMPORAL")
        self.separador()
        temporal = analisar_periodos(
            df,
            classificacao["campos"],
            granularidade=config.get("periodo", "automatico"),
        )

        if temporal.get("aviso"):
            self.log(f"[AVISO] {temporal['aviso']}")
        self.log(f"[INFO] Granularidade: {temporal.get('granularidade_aplicada', 'mensal')}")

        periodos = temporal.get("periodos", [])
        self.log(f"[OK] Períodos identificados: {len(periodos)}")
        formato = temporal.get("formato", "numero")
        for periodo in periodos:
            valor = periodo["valor"]
            valor_formatado = (
                f"R$ {valor:,.2f}"
                if formato == "moeda"
                else f"{valor:,.2f}"
            )
            self.log(f"[+] {periodo['periodo']}: {valor_formatado}")

        comparacoes = temporal.get("comparacoes", [])
        if comparacoes:
            self.log("-" * 40)
            self.log("VARIAÇÕES ENTRE PERÍODOS")
            self.log("-" * 40)
            for comparacao in comparacoes:
                variacao = comparacao["variacao_percentual"]
                texto = "indefinida" if variacao is None else f"{variacao:+.2f}%"
                self.log(
                    f"[+] {comparacao['periodo_anterior']} → "
                    f"{comparacao['periodo_atual']}: {texto}"
                )

        return temporal
