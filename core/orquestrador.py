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

Logger = Callable[[str], None]
ProgressCallback = Callable[[int, str], None]

MODULOS_PADRAO = {
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
    ) -> None:
        self._logger = logger or (lambda _mensagem: None)
        self._progresso = progresso or (lambda _valor, _mensagem: None)

    def log(self, mensagem: str = "") -> None:
        self._logger(str(mensagem))

    def progresso(self, valor: int, mensagem: str) -> None:
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
        if fonte != "computador":
            raise NotImplementedError(
                f"A fonte '{fonte}' ainda não está implementada. "
                "Utilize 'Computador' nesta versão."
            )

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

        analise_estrutural = self._executar_estrutural(df_consolidado, config)
        analise_qualidade = self._executar_qualidade(df_consolidado, config)
        classificacao = self._executar_classificacao(df_consolidado, config)
        indicadores = self._executar_indicadores(df_consolidado, classificacao, config)
        analise_temporal = self._executar_temporal(df_consolidado, classificacao, config)

        resultado = {
            "arquivos": caminhos,
            "configuracao": deepcopy(config),
            "resultados_arquivos": resultados_arquivos,
            "dataframe": df_consolidado,
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

    def _executar_qualidade(self, df: pd.DataFrame, config: dict) -> dict | None:
        if not config["modulos"]["qualidade"]:
            self.log("[INFO] Qualidade dos dados desativada na configuração.")
            return None

        self.progresso(54, "Analisando qualidade dos dados...")
        self.separador()
        self.log("QUALIDADE DOS DADOS")
        self.separador()
        qualidade = analisar_qualidade(df)
        self.log(f"[+] Completude: {qualidade['completude']:.2f}%")
        self.log(f"[+] Valores ausentes: {qualidade['valores_ausentes']}")
        self.log(f"[+] Linhas com dados ausentes: {qualidade['linhas_com_ausentes']}")
        self.log(f"[+] Registros duplicados: {qualidade['linhas_duplicadas']}")
        self.log(f"[+] Colunas totalmente vazias: {qualidade['quantidade_colunas_vazias']}")
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
        self._registrar_indicadores_vendas(indicadores)
        return indicadores

    def _registrar_indicadores_vendas(self, indicadores: dict) -> None:
        self.separador()
        self.log("RESUMO FINANCEIRO")
        self.separador()
        campos = (
            ("faturamento_total", "Faturamento total", "moeda"),
            ("total_vendas", "Total de vendas", "inteiro"),
            ("quantidade_total", "Quantidade vendida", "inteiro"),
            ("ticket_medio", "Ticket médio", "moeda"),
            ("preco_medio_unidade", "Preço médio/unidade", "moeda"),
        )
        for chave, rotulo, tipo in campos:
            if chave not in indicadores:
                continue
            valor = indicadores[chave]
            if tipo == "moeda":
                self.log(f"[+] {rotulo}: R$ {valor:,.2f}")
            else:
                self.log(f"[+] {rotulo}: {valor:,.0f}")

        self.log("-" * 40)
        self.log("DESTAQUES")
        self.log("-" * 40)
        if "produto_maior_faturamento" in indicadores:
            self.log(f"[+] Produto líder: {indicadores['produto_maior_faturamento']}")
            self.log(f"    Faturamento: R$ {indicadores['valor_produto_lider']:,.2f}")
        if "loja_maior_faturamento" in indicadores:
            self.log(f"[+] Loja líder: {indicadores['loja_maior_faturamento']}")
            self.log(f"    Faturamento: R$ {indicadores['valor_loja_lider']:,.2f}")

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
