"""Edição direta e exportação para grades em que a metáfora tabular faz sentido."""

from __future__ import annotations

import csv
import io
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox


class EditorGrade:
    def __init__(self, tree, *, colunas_editaveis, salvar, parent=None, titulo="Grade"):
        self.tree = tree
        self.colunas_editaveis = set(colunas_editaveis)
        self.salvar = salvar
        self.parent = parent or tree.winfo_toplevel()
        self.titulo = titulo
        self._editor = None
        tree.bind("<Double-1>", self._duplo_clique, add="+")

    def _duplo_clique(self, evento):
        if self._editor is not None:
            self._fechar_editor()
        if self.tree.identify_region(evento.x, evento.y) != "cell":
            return
        iid = self.tree.identify_row(evento.y)
        coluna_visual = self.tree.identify_column(evento.x)
        if not iid or not coluna_visual:
            return
        indice = int(coluna_visual.removeprefix("#")) - 1
        colunas = list(self.tree["columns"])
        if indice < 0 or indice >= len(colunas):
            return
        chave = str(colunas[indice])
        if chave not in self.colunas_editaveis:
            return
        bbox = self.tree.bbox(iid, coluna_visual)
        if not bbox:
            return
        x, y, w, h = bbox
        valor = self.tree.set(iid, chave)
        editor = tk.Entry(self.tree, relief="solid", bd=1)
        editor.insert(0, valor)
        editor.select_range(0, "end")
        editor.place(x=x, y=y, width=w, height=h)
        editor.focus_set()
        self._editor = editor
        editor.bind("<Escape>", lambda _e: self._fechar_editor())
        editor.bind("<FocusOut>", lambda _e: self._confirmar(iid, chave))
        editor.bind("<Return>", lambda _e: self._confirmar(iid, chave))

    def _fechar_editor(self):
        if self._editor is not None:
            try:
                self._editor.destroy()
            except tk.TclError:
                pass
            self._editor = None

    def _confirmar(self, iid, chave):
        if self._editor is None:
            return
        valor = self._editor.get().strip()
        self._fechar_editor()
        try:
            self.salvar(iid, chave, valor)
            if self.tree.exists(iid):
                self.tree.set(iid, chave, valor)
        except (ValueError, PermissionError, RuntimeError) as erro:
            messagebox.showerror(self.titulo, str(erro), parent=self.parent)

    def _linhas_exportacao(self):
        colunas = list(self.tree["columns"])
        cabecalho = [self.tree.heading(c).get("text") or c for c in colunas]
        linhas = [[self.tree.set(iid, c) for c in colunas] for iid in self.tree.get_children()]
        return colunas, cabecalho, linhas

    def _salvar_no_servidor(self, conteudo: bytes, nome: str, formato: str):
        from core.nodo import usa_servidor_remoto
        if not usa_servidor_remoto():
            return None
        from services.servidor_cliente import enviar_bytes_servidor
        resultado = enviar_bytes_servidor(
            conteudo, nome, modulo="grade", categoria=f"exportacao-grade-{formato.lower()}",
        )
        messagebox.showinfo(
            self.titulo,
            f"Exportação armazenada no Servidor Corporativo.\n\nArquivo: {resultado.get('nome', nome)}\nID: {resultado.get('id', '—')}",
            parent=self.parent,
        )
        return resultado

    def exportar_csv(self, destino=None):
        from core.nodo import usa_servidor_remoto
        _colunas, cabecalho, linhas = self._linhas_exportacao()
        if usa_servidor_remoto():
            buffer = io.StringIO(newline="")
            escritor = csv.writer(buffer, delimiter=";")
            escritor.writerow(cabecalho)
            escritor.writerows(linhas)
            nome = f"{self.titulo.strip().replace(' ', '_') or 'grade'}.csv"
            return self._salvar_no_servidor(buffer.getvalue().encode("utf-8-sig"), nome, "csv")

        if destino is None:
            destino = filedialog.asksaveasfilename(
                parent=self.parent, title=f"Exportar {self.titulo}", defaultextension=".csv",
                filetypes=(("CSV", "*.csv"),),
            )
        if not destino:
            return None
        caminho = Path(destino)
        with caminho.open("w", newline="", encoding="utf-8-sig") as arquivo:
            escritor = csv.writer(arquivo, delimiter=";")
            escritor.writerow(cabecalho)
            escritor.writerows(linhas)
        return caminho

    def exportar_xlsx(self, destino=None):
        from core.nodo import usa_servidor_remoto
        try:
            from openpyxl import Workbook
        except ImportError as erro:
            raise RuntimeError("openpyxl é necessário para exportar XLSX.") from erro
        wb = Workbook(); ws = wb.active; ws.title = self.titulo[:31]
        _colunas, cabecalho, linhas = self._linhas_exportacao()
        ws.append(cabecalho)
        for linha in linhas:
            ws.append(linha)

        if usa_servidor_remoto():
            buffer = io.BytesIO()
            wb.save(buffer)
            nome = f"{self.titulo.strip().replace(' ', '_') or 'grade'}.xlsx"
            return self._salvar_no_servidor(buffer.getvalue(), nome, "xlsx")

        if destino is None:
            destino = filedialog.asksaveasfilename(
                parent=self.parent, title=f"Exportar {self.titulo}", defaultextension=".xlsx",
                filetypes=(("Excel", "*.xlsx"),),
            )
        if not destino:
            return None
        wb.save(destino)
        return Path(destino)

