import tkinter as tk
from interface.app import AplicacaoAutomacao

def main():
    janela = tk.Tk()
    app = AplicacaoAutomacao(
        janela
    )

    janela.mainloop()
if __name__ == '__main__':
    main()