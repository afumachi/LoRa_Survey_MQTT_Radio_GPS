# FEE247 - Desenvolvimento de Soluções IoT com LoRa e LoRaWAN
#======= Nível 6 - Gerência e Parâmetros LoRa ============
# Gráficos de RSSI e PSR

import time
import os
import tkinter.messagebox as tkMessageBox
import tkinter.filedialog as tkFileDialog
import tkinter.ttk as ttk
import tkinter

from tkinter import *
import matplotlib
matplotlib.use('TkAgg')
from matplotlib import style
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import math

style.use("ggplot")

dir_nivel4 = os.path.join(os.path.dirname(__file__), '../3_N4_Armazenamento/Parametros/')

# =============================================================================
# REFRESH das telas
# =============================================================================

REFRESH_MS = 500   # Intervalo de atualização dos gráficos [ms] (200 ms)

# Intervalo de atualização do status/contador de medidas da aba "Mapa Calor
# LoRa" (verificação de PARAMETROS.txt + leitura de N5_log_cobertura.txt).
# Essa aba não exibe telemetria em tempo real (o mapa só é (re)desenhado
# quando o operador clica em "Gerar Mapa de Calor"), então não precisa do
# mesmo ritmo de 500 ms das abas de gráficos ao vivo. Um intervalo mais
# longo aqui reduz a carga de I/O + parsing de arquivo repetida, que
# estava competindo por CPU com as demais atualizações e causando
# lentidão perceptível na interface (inclusive no cursor do mouse).
REFRESH_MAPA_MS = 2000

# Número de medidas amostradas nos gráficos por padrão (ajustável pelo
# operador no campo "Amostragem" da aba Gerência LoRa). Todas as 4 abas
# gráficas (Aplicação, Gerência, Gerência Completa, Taxas de Dados) usam
# esse mesmo valor para decidir quantas das medidas mais recentes exibir.
JANELA_AMOSTRAGEM_PADRAO = 1000
MAX_PONTOS = 1000


cor_rssi_down = "#1f77b4"
cor_rssi_up = "#ff7f0e"
cor_snr_down = "#1f77b4"
cor_snr_up = "#ff7f0e"
cor_psr = "#2ca02c"

# ===================== ATUALIZA GRÁFICOS =====================
def atualizar_grafico(ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz, label_down, label_up, label_snr_down, label_snr_up, label_psr):
    rssi_down = []
    rssi_up = []
    snr_down = []
    snr_up = []   
    psr = []

    # ===================== RSSI =====================
    try:
        with open("../3_N4_Armazenamento/Dados_Processados/rssi.tmp", 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        partes = linha.split()
                        down = float(partes[0].replace(",", "."))
                        up = float(partes[1].replace(",", "."))
                        snr_dl_down = float(partes[2].replace(",", "."))
                        snr_ul_up = float(partes[3].replace(",", "."))                        
                        rssi_down.append(down)
                        rssi_up.append(up)
                        snr_down.append(snr_dl_down)
                        snr_up.append(snr_ul_up)                        
                    except:
                        pass
    except FileNotFoundError:
        pass

    # ===================== PSR =====================
    try:
        with open("../3_N4_Armazenamento/Dados_Processados/psr.tmp", 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        psr.append(float(linha))
                    except ValueError:
                        pass
    except FileNotFoundError:
        pass

    # ===================== JANELA DESLIZANTE =====================
    rssi_down = rssi_down[-MAX_PONTOS:]
    rssi_up = rssi_up[-MAX_PONTOS:]
    snr_down = snr_down[-MAX_PONTOS:]
    snr_up = snr_up[-MAX_PONTOS:]    
    psr = psr[-MAX_PONTOS:]

    # ===================== LABELS =====================
    if rssi_down:
        label_down.config(text="RSSI DL atual: " + str(round(rssi_down[-1],2)) + " dBm")
    else:
        label_down.config(text="RSSI DL atual: --")

    if rssi_up:
        label_up.config(text="RSSI UL atual: " + str(round(rssi_up[-1],2)) + " dBm")
    else:
        label_up.config(text="RSSI UL atual: --")

    if snr_down:
        label_snr_down.config(text="SNR DL atual: " + str(round(snr_down[-1],2)) + " dB")
    else:
        label_snr_down.config(text="SNR DL atual: --")

    if snr_up:
        label_snr_up.config(text="SNR UL atual: " + str(round(snr_up[-1],2)) + " dB")
    else:
        label_snr_up.config(text="SNR UL atual: --")

    if psr:
        label_psr.config(text="PSR atual: " + str(round(psr[-1],2)) + " %")
    else:
        label_psr.config(text="PSR atual: --")

    # ===================== GRÁFICO RSSI =====================
    ax1.clear()
    if rssi_down:
        ax1.plot(
            rssi_down,
            label="RSSI Downlink (dBm)",
            linewidth=1.5,
            marker='o',
            markersize=3,
            color=cor_rssi_down
        )
    if rssi_up:
        ax1.plot(
            rssi_up,
            label="RSSI Uplink (dBm)",
            linewidth=1.5,
            marker='s',
            markersize=3,
            color=cor_rssi_up
        )
    if rssi_down or rssi_up:
        ax1.legend(loc='upper right')
        todos_rssi = rssi_down + rssi_up
        val_min = min(todos_rssi)
        val_max = max(todos_rssi)
        margem = (val_max - val_min) * 0.10
        if margem == 0:
            margem = 5
        ax1.set_ylim(val_min - margem, val_max + margem)

    ax1.legend(fontsize=8)
    ax1.set_title("RSSI LoRa (Downlink / Uplink)", fontsize=10)
    ax1.set_ylabel("RSSI (dBm)")
    ax1.set_xlabel("Últimas " + str(MAX_PONTOS) + " medidas")

    # ===================== GRÁFICO SNR =====================
    ax2.clear()
    if snr_down:
        ax2.plot(
            snr_down,
            label="SNR Downlink (dBm)",
            linewidth=1.5,
            marker='o',
            markersize=3,
            color=cor_snr_down
        )
    if snr_up:
        ax2.plot(
            snr_up,
            label="SNR Uplink (dBm)",
            linewidth=1.5,
            marker='s',
            markersize=3,
            color=cor_snr_up
        )
    if snr_down or snr_up:
        ax2.legend(loc='upper right')
        todos_snr = snr_down + snr_up
        val_snr_min = min(todos_snr)
        val_snr_max = max(todos_snr)
        margem_snr = (val_snr_max - val_snr_min) * 0.10
        if margem == 0:
            margem = 5
        ax2.set_ylim(val_snr_min - margem_snr, val_snr_max + margem_snr)

    ax2.legend(fontsize=8)
    ax2.set_title("SNR LoRa (Downlink / Uplink)", fontsize=10)
    ax2.set_ylabel("SNR (dB)")
    ax2.set_xlabel("Últimas " + str(MAX_PONTOS) + " medidas")

    # ===================== GRÁFICO PSR =====================
    ax3.clear()
    if psr:
        ax3.plot(
            psr,
            label="PSR (%)",
            linewidth=1.5,
            marker='o',
            markersize=3,
            color=cor_psr
        )
        ax3.legend(loc='upper right')
        val_min = min(psr)
        val_max = max(psr)
        margem = (val_max - val_min) * 0.10
        if margem == 0:
            margem = 5
        ax3.set_ylim(max(0, val_min - margem), min(105, val_max + margem))

    ax3.legend(fontsize=8)
    ax3.set_title("Packet Success Rate - PSR", fontsize=10)
    ax3.set_ylabel("PSR (%)")
    ax3.set_xlabel("Últimas " + str(MAX_PONTOS) + " medidas")

    # ===================== ATUALIZA =====================
    canvas1.draw()
    canvas2.draw()
    canvas3.draw()
    raiz.after(1000,atualizar_grafico,ax1,ax2,ax3,canvas1,canvas2,canvas3,raiz,label_down,label_up,label_snr_down,label_snr_up,label_psr)

# ===================== BOTÕES =====================
def salvar(fig1, fig2, fig3):
    arquivo = filedialog.asksaveasfilename(defaultextension=".png")
    if arquivo:
        fig1.savefig(arquivo.replace(".png","_rssi.png"))
        fig2.savefig(arquivo.replace(".png","_snr.png"))
        fig3.savefig(arquivo.replace(".png","_psr.png"))

# ===================== INTERFACE =====================
raiz = Tk()
raiz.title("FEE230 - NÍVEL 6 - GERÊNCIA LORA")
raiz.geometry("1350x980")
raiz.resizable(True, True)


# =============================================================================
# NOTEBOOK (ABAS)
# =============================================================================
notebook = ttk.Notebook(raiz)
notebook.pack(fill=BOTH, expand=True, padx=5, pady=5)

# Estilo das abas
style_ttk = ttk.Style()
style_ttk.configure("TNotebook.Tab", font=("Arial", 12, "bold"), padding=[12, 6])


# =============================================================================
# ABA 1: Parâmetros de Radio LoRa
# =============================================================================
aba_gerencia = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_gerencia, text="  📡 LoRa Site Survey - Parâmetros de Rádio ")

# --- PARAMETRIZAÇÃO ---
reg_parametrizacao = Frame(master=aba_gerencia, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_parametrizacao.place(x=10, y=10, width=300, height=380)

Label(reg_parametrizacao, font=("Arial", 14, "bold"), text="Configurações LoRa",
      padx=5, pady=5, bg="#F0F0F0").pack(side=TOP, anchor="n")

# Qtde. de Medidas
Label(reg_parametrizacao, text="Qtde. de Medidas", font=("Arial", 12),
      bg="#F0F0F0").place(x=20, y=40)
valor_intervalo = Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_intervalo.place(x=170, y=40)
valor_intervalo.insert(0, "10")

# Tempo de Rádio
Label(reg_parametrizacao, text="Tempo de Rádio", font=("Arial", 12),
      bg="#F0F0F0").place(x=20, y=75)
Label(reg_parametrizacao, text="Em segundos", font=("Arial", 8),
      bg="#F0F0F0").place(x=30, y=95)
valor_tempo_tx_rx = Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_tempo_tx_rx.place(x=170, y=75)
valor_tempo_tx_rx.insert(0, "8")

# Spreading Factor
Label(reg_parametrizacao, text="Spreading Factor", font=("Arial", 12),
      bg="#F0F0F0").place(x=20, y=110)
Label(reg_parametrizacao, text="7 a 12", font=("Arial", 8), bg="#F0F0F0").place(x=30, y=130)
valor_spreadingfactor = Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_spreadingfactor.place(x=170, y=110)
valor_spreadingfactor.insert(0, "12")

# Bandwidth
Label(reg_parametrizacao, text="Bandwidth", font=("Arial", 12),
      bg="#F0F0F0").place(x=20, y=145)
Label(reg_parametrizacao, text="125, 250, 500 kHz", font=("Arial", 8),
      bg="#F0F0F0").place(x=30, y=165)
valor_bandwidth = Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_bandwidth.place(x=170, y=145)
valor_bandwidth.insert(0, "125")

# CodingRate
Label(reg_parametrizacao, text="CodingRate", font=("Arial", 12),
      bg="#F0F0F0").place(x=20, y=180)
Label(reg_parametrizacao, text="5 a 8 => 4/5, 4/6, 4/7, 4/8", font=("Arial", 8),
      bg="#F0F0F0").place(x=30, y=200)
valor_codingrate = Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_codingrate.place(x=170, y=180)
valor_codingrate.insert(0, "8")

# Potência
Label(reg_parametrizacao, text="Potência de Rádio", font=("Arial", 12),
      bg="#F0F0F0").place(x=20, y=215)
Label(reg_parametrizacao, text="2 a 20dBm", font=("Arial", 8),
      bg="#F0F0F0").place(x=30, y=235)
valor_potencia_radio = Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_potencia_radio.place(x=170, y=215)
valor_potencia_radio.insert(0, "14")

# Status
status_texto_ger = StringVar()
status_texto_ger.set("AGUARDANDO...")
label_status_ger = Label(reg_parametrizacao, textvariable=status_texto_ger,
                         font=("Arial", 10, "bold"), fg="gray", bg="#F0F0F0")
label_status_ger.place(x=25, y=300)



# --- FUNÇÕES DE CAPTURA E GRAVAÇÃO ---
def captura_num_medidas():
    v = valor_intervalo.get()
    n = int(v) if v else 0
    return int(n) if n > 0 else 10


def captura_num_spreadingfactor():
    v = valor_spreadingfactor.get()
    n = int(v) if v else 12
    return max(7, min(12, int(n)))


def captura_num_bandwidth():
    v = valor_bandwidth.get()
    n = int(v) if v else 125
    if n < 200:
        return 125
    elif n < 350:
        return 250
    else:
        return 500


def captura_num_codingrate():
    v = valor_codingrate.get()
    n = int(v) if v else 8
    return max(5, min(8, int(n)))


def captura_num_potencia_radio():
    v = valor_potencia_radio.get()
    n = int(v) if v else 20
    return max(2, min(20, int(n)))


def captura_num_tempo_tx_rx():
    v = valor_tempo_tx_rx.get()
    n = int(v) if v else 8
    return max(1, min(10, int(n)))


def grava_comandos(condicao_start):
    arquivo_txt = os.path.join(dir_nivel4, 'PARAMETROS.txt')
    s = open(arquivo_txt, 'w')
    s.write(str(condicao_start) + "\n")
    s.write(str(captura_num_medidas()) + "\n")
    s.write(str(captura_num_spreadingfactor()) + "\n")
    s.write(str(captura_num_bandwidth()) + "\n")
    s.write(str(captura_num_codingrate()) + "\n")
    s.write(str(captura_num_potencia_radio()) + "\n")
    s.write(str(captura_num_tempo_tx_rx()) + "\n")
    s.close()


def iniciar_teste():
    grava_comandos(1)
    status_texto_ger.set("LoRa Site Survey - Wisstek-IoT")
    label_status_ger.config(fg="red")


btn_iniciar = Button(reg_parametrizacao, text="INICIAR TESTE", font=("Arial", 13, "bold"), width=20, command=iniciar_teste)
btn_iniciar.place(x=25, y=260)

    
path_param = os.path.join(dir_nivel4, 'PARAMETROS.txt')
if os.path.exists(path_param):
    try:
        pp = open(path_param, 'r')
        status_lido = pp.readline().strip()
        pp.close()
        if status_lido == '0':
            status_texto_ger.set("LoRa Site Survey - Wisstek-IoT")
            label_status_ger.config(fg="red")
            pp.close()
        #if lss_status == "0":
        #    lss_status_texto.set("LSS PARADO")
        #    label_lss_status.config(fg="green")
    except Exception:
        pass



# =============================================================================
# ABA 2: GERÊNCIA LoRa (RSSI/SNR em tempo real - dados do Nível 5)
# =============================================================================
aba_gerencia_completa = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_gerencia_completa, text="  📶 Gerência de Rede LoRa  ")


# ===================== LABELS DAS RSSIS =====================
frame_labels_rssi = Frame(aba_gerencia_completa)
frame_labels_rssi.pack(fill="x", padx=10, pady=(10,5))

label_down = Label(
    frame_labels_rssi,
    text="RSSI DL atual: --",
    font=("Arial",10,"bold"),
    bg=cor_rssi_down,
    fg="white",
    relief="ridge",
    bd=3,
    width=20,
    pady=4
)
label_down.pack(side="left", padx=5)

label_up = Label(
    frame_labels_rssi,
    text="RSSI UL atual: --",
    font=("Arial",10,"bold"),
    bg=cor_rssi_up,
    fg="white",
    relief="ridge",
    bd=3,
    width=20,
    pady=4
)
label_up.pack(side="left", padx=5)

# ===================== BOTÃO SALVAR =====================
btn = Button(
    frame_labels_rssi,
    text="Salvar Gráficos",
    command=lambda: salvar(fig1, fig2, fig3)
)
btn.pack(side="right", pady=5)

# ===================== GRÁFICO DAS RSSIS =====================
frame_rssi = Frame(aba_gerencia_completa)
frame_rssi.pack(fill="both", expand=True, padx=10, pady=5)

fig1 = Figure(figsize=(10,1.8))
ax1 = fig1.add_subplot(111)

canvas1 = FigureCanvasTkAgg(fig1, master=frame_rssi)
canvas1.get_tk_widget().pack(fill="both", expand=True)

# ===================== LABELS DAS SNRS =====================
frame_labels_snr = Frame(aba_gerencia_completa)
frame_labels_snr.pack(fill="x", padx=10, pady=(10,5))

label_snr_down = Label(
    frame_labels_snr,
    text="SNR DL atual: --",
    font=("Arial",10,"bold"),
    bg=cor_snr_down,
    fg="white",
    relief="ridge",
    bd=3,
    width=20,
    pady=4
)
label_snr_down.pack(side="left", padx=5)

label_snr_up = Label(
    frame_labels_snr,
    text="SNR UL atual: --",
    font=("Arial",10,"bold"),
    bg=cor_snr_up,
    fg="white",
    relief="ridge",
    bd=3,
    width=20,
    pady=4
)
label_snr_up.pack(side="left", padx=5)

# ===================== GRÁFICO DAS SNRS =====================
frame_snr = Frame(aba_gerencia_completa)
frame_snr.pack(fill="both", expand=True, padx=10, pady=5)

fig2 = Figure(figsize=(10,1.8))
ax2 = fig2.add_subplot(111)

canvas2 = FigureCanvasTkAgg(fig2, master=frame_snr)
canvas2.get_tk_widget().pack(fill="both", expand=True)

# ===================== LABEL DA PSR =====================
frame_label_psr = Frame(aba_gerencia_completa)
frame_label_psr.pack(fill="x", padx=10, pady=5)

label_psr = Label(
    frame_label_psr,
    text="PSR atual: --",
    font=("Arial",10,"bold"),
    bg=cor_psr,
    fg="white",
    relief="ridge",
    bd=3,
    width=15,
    pady=4
)
label_psr.pack(side="left", padx=5)

# ===================== GRÁFICO DA PSR =====================
frame_psr = Frame(aba_gerencia_completa)
frame_psr.pack(fill="both", expand=True, padx=10, pady=5)

fig3 = Figure(figsize=(10,1.8))
ax3 = fig3.add_subplot(111)

canvas3 = FigureCanvasTkAgg(fig3, master=frame_psr)
canvas3.get_tk_widget().pack(fill="both", expand=True)


atualizar_grafico(ax1,ax2,ax3,canvas1,canvas2,canvas3,raiz,label_down,label_up,label_snr_down,label_snr_up,label_psr)


# =============================================================================
# CALLBACK DE FECHAR JANELA
# =============================================================================
def callback():
    if tkMessageBox.askokcancel("Sair", "Tem certeza que deseja sair?"):
        grava_comandos(0)
        raiz.destroy()


raiz.protocol("WM_DELETE_WINDOW", callback)
raiz.mainloop()
raiz.update_idletasks()
