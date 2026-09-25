# FEE247 - Desenvolvimento de Soluções IoT com LoRa e LoRaWAN
# ======= Nível 6 - Gerência e Parâmetros LoRa ============
# Gráficos de RSSI, PSR, GPS e Cadastro de End Devices

import time
import os
import glob
import re
import webbrowser
import tkinter.messagebox as tkMessageBox
import tkinter.filedialog as tkFileDialog
import tkinter.ttk as ttk
import tkinter
from tkinter import *
from tkinter import messagebox

import matplotlib
matplotlib.use('TkAgg')
from matplotlib import style
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import math

import pandas as pd

style.use("ggplot")

# =============================================================================
# DIRETÓRIOS E CONSTANTES
# =============================================================================
dir_nivel4 = os.path.join(os.path.dirname(__file__), '../3_N4_Armazenamento/Parametros/')

arquivo_gw_gps = os.path.join(dir_nivel4, "gateway_gps.txt")

dir_dados = os.path.join(os.path.dirname(__file__), '../3_N4_Armazenamento/Dados_Processados/')
arquivo_gps_tmp = os.path.join(dir_dados, "gps.tmp")

# Caminho para o CSV de End Devices
arquivo_csv_end_devices = os.path.join(dir_nivel4, "end_devices_net_par.csv")

# Valores de fallback padrão - GPS
GW_LAT_DEFAULT = -23.005380
GW_LON_DEFAULT = -46.835336
GW_ALT_DEFAULT = 770.0

# =============================================================================
# REFRESH DAS TELAS E CONFIGURAÇÕES
# =============================================================================
REFRESH_MS = 500
MAX_PONTOS = 10000

cor_rssi_down = "#1f77b4"
cor_rssi_up = "#ff7f0e"
cor_snr_down = "#1f77b4"
cor_snr_up = "#ff7f0e"
cor_psr = "#2ca02c"
cor_taxa_teorica = "#9467bd"
cor_taxa_calculada = "#d62728"

# Atualiza arquivo de Parâmetros
pasta_parametros = os.path.join(dir_nivel4, 'PARAMETROS.txt')
os.makedirs(dir_nivel4, exist_ok=True)
with open(pasta_parametros, 'w') as parametros:
    parametros.write("0\n0\n12\n125\n8\n20\n8\n0\n0\n") 

estado_lss = "0"

def ler_end_devices():
    """Lê a lista de End Devices cadastrados no CSV para popular o Dropdown."""
    end_devices = []
    if os.path.exists(arquivo_csv_end_devices):
        try:
            df_devices = pd.read_csv(arquivo_csv_end_devices)
            if "endereco_rede" in df_devices.columns:
                for val in df_devices["endereco_rede"]:
                    val_str = str(val).strip()
                    if val_str.startswith("0x") or val_str.startswith("0X"):
                        end_devices.append(int(val_str, 16))
                    else:
                        end_devices.append(int(val_str))
        except Exception as e:
            print(f"[ERRO] Falha ao ler CSV: {e}")
    
    if not end_devices:
        end_devices = [1]
    return sorted(list(set(end_devices)))

def get_tmp_path(nome_base):
    """Monta o caminho dinâmico do arquivo com o prefixo do End Device."""
    dev_id = end_device_selecionado.get()
    return os.path.join(dir_dados, f"{dev_id}_{nome_base}")


# =============================================================================
# FUNÇÕES DE LEITURA (GPS)
# =============================================================================
def ler_gateway_gps():
    gw_lat, gw_lon, gw_alt = GW_LAT_DEFAULT, GW_LON_DEFAULT, GW_ALT_DEFAULT
    if os.path.exists(arquivo_gw_gps):
        try:
            with open(arquivo_gw_gps, "r") as f:
                conteudo = f.read()
            valores_dict = {}
            for linha in conteudo.splitlines():
                if "=" in linha and not linha.strip().startswith("#"):
                    chave, val = linha.split("=", 1)
                    try:
                        valores_dict[chave.strip().upper()] = float(val.strip())
                    except ValueError:
                        pass
            if "GW_LAT" in valores_dict and "GW_LON" in valores_dict:
                gw_lat = valores_dict["GW_LAT"]
                gw_lon = valores_dict["GW_LON"]
                gw_alt = valores_dict.get("GW_ALT", gw_alt)
                return gw_lat, gw_lon, gw_alt
            floats = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", conteudo)]
            if len(floats) >= 3:
                gw_lat, gw_lon, gw_alt = floats[0], floats[1], floats[2]
            elif len(floats) == 2:
                gw_lat, gw_lon = floats[0], floats[1]
        except Exception as e:
            print(f"Erro ao ler {arquivo_gw_gps}: {e}")
    return gw_lat, gw_lon, gw_alt

def ler_ultimo_gps():
    caminho_arquivo = get_tmp_path("gps.tmp")
    if not os.path.exists(caminho_arquivo):
        return None
    try:
        with open(caminho_arquivo, "r") as f:
            linhas = [line.strip() for line in f if line.strip()]
            if not linhas:
                return None
            partes = linhas[-1].split()
            if len(partes) >= 4:
                return (float(partes[0]), float(partes[1]), float(partes[2]), float(partes[3]))
            elif len(partes) == 3:
                return float(partes[0]), float(partes[1]), float(partes[2]), None
    except Exception as e:
        print(f"Erro ao ler o arquivo {caminho_arquivo}: {e}")
        return None


# ===================== ATUALIZA GRÁFICOS (LORA) =====================
def atualizar_grafico(ax1, ax2, ax3, ax4, canvas1, canvas2, canvas3, canvas4, raiz, label_down, label_up, label_snr_down, label_snr_up, label_psr, label_taxa_teorica, label_taxa_calculada):
    rssi_down, rssi_up, snr_down, snr_up = [], [], [], []
    psr, taxa_teorica, taxa_calculada = [], [], []

    try:
        with open(get_tmp_path("rssi.tmp"), 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        partes = linha.split()
                        rssi_down.append(float(partes[0].replace(",", ".")))
                        rssi_up.append(float(partes[1].replace(",", ".")))
                        snr_down.append(float(partes[2].replace(",", ".")))
                        snr_up.append(float(partes[3].replace(",", ".")))                        
                    except:
                        pass
    except FileNotFoundError: pass

    try:
        with open(get_tmp_path("psr.tmp"), 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try: psr.append(float(linha))
                    except ValueError: pass
    except FileNotFoundError: pass

    try:
        with open(get_tmp_path("taxa_dados.tmp"), 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        partes = linha.split()
                        t_teorica = partes[0].replace(",", ".")
                        t_calculada = partes[1].replace(",", ".")
                        if t_teorica != "None" and t_calculada != "None":
                            taxa_teorica.append(float(t_teorica))
                            taxa_calculada.append(float(t_calculada))
                    except (ValueError, IndexError): pass
    except FileNotFoundError: pass

    # Janela Deslizante
    rssi_down = rssi_down[-MAX_PONTOS:]
    rssi_up = rssi_up[-MAX_PONTOS:]
    snr_down = snr_down[-MAX_PONTOS:]
    snr_up = snr_up[-MAX_PONTOS:]    
    psr = psr[-MAX_PONTOS:]
    taxa_teorica = taxa_teorica[-MAX_PONTOS:]
    taxa_calculada = taxa_calculada[-MAX_PONTOS:]

    # Labels
    label_down.config(text=f"RSSI DL atual: {round(rssi_down[-1],2)} dBm" if rssi_down else "RSSI DL atual: --")
    label_up.config(text=f"RSSI UL atual: {round(rssi_up[-1],2)} dBm" if rssi_up else "RSSI UL atual: --")
    label_snr_down.config(text=f"SNR DL atual: {round(snr_down[-1],2)} dB" if snr_down else "SNR DL atual: --")
    label_snr_up.config(text=f"SNR UL atual: {round(snr_up[-1],2)} dB" if snr_up else "SNR UL atual: --")
    label_psr.config(text=f"PSR atual: {round(psr[-1],2)} %" if psr else "PSR atual: --")
    label_taxa_teorica.config(text=f"Taxa Teórica atual: {round(taxa_teorica[-1],3)} bps" if taxa_teorica else "Taxa Teórica atual: --")
    label_taxa_calculada.config(text=f"Taxa Real atual: {round(taxa_calculada[-1],3)} bps" if taxa_calculada else "Taxa Real atual: --")

    # Gráficos
    ax1.clear(); ax2.clear(); ax3.clear(); ax4.clear()
    
    if rssi_down: ax1.plot(rssi_down, label="RSSI Downlink (dBm)", linewidth=1.5, marker='o', markersize=2, color=cor_rssi_down)
    if rssi_up: ax1.plot(rssi_up, label="RSSI Uplink (dBm)", linewidth=1.5, marker='s', markersize=2, color=cor_rssi_up)
    if rssi_down or rssi_up:
        ax1.legend(loc='upper right', fontsize=8)
        val_min, val_max = min(rssi_down + rssi_up), max(rssi_down + rssi_up)
        margem = (val_max - val_min) * 0.10 or 5
        ax1.set_ylim(val_min - margem, val_max + margem)
    ax1.set_title("RSSI LoRa (Downlink / Uplink)", fontsize=9); ax1.set_ylabel("RSSI (dBm)", fontsize=9); ax1.tick_params(axis='both', labelsize=7)    

    if snr_down: ax2.plot(snr_down, label="SNR Downlink (dB)", linewidth=1.5, marker='o', markersize=2, color=cor_snr_down)
    if snr_up: ax2.plot(snr_up, label="SNR Uplink (dB)", linewidth=1.5, marker='s', markersize=2, color=cor_snr_up)
    if snr_down or snr_up:
        ax2.legend(loc='upper right', fontsize=8)
        val_snr_min, val_snr_max = min(snr_down + snr_up), max(snr_down + snr_up)
        margem_snr = (val_snr_max - val_snr_min) * 0.10 or 5
        ax2.set_ylim(val_snr_min - margem_snr, val_snr_max + margem_snr)
    ax2.set_title("SNR LoRa (Downlink / Uplink)", fontsize=9); ax2.set_ylabel("SNR (dB)", fontsize=9); ax2.tick_params(axis='both', labelsize=7)    

    if psr:
        ax3.plot(psr, label="PSR (%)", linewidth=1.5, marker='o', markersize=2, color=cor_psr)
        ax3.legend(loc='upper right', fontsize=8)
        val_min, val_max = min(psr), max(psr)
        margem = (val_max - val_min) * 0.10 or 5
        ax3.set_ylim(max(0, val_min - margem), min(105, val_max + margem))
    ax3.set_title("Packet Success Rate - PSR", fontsize=9); ax3.set_ylabel("PSR (%)", fontsize=9); ax3.tick_params(axis='both', labelsize=7)   

    if taxa_teorica: ax4.plot(taxa_teorica, label="Taxa Teórica (bps)", linewidth=1.5, marker='o', markersize=2, color=cor_taxa_teorica)
    if taxa_calculada: ax4.plot(taxa_calculada, label="Taxa Real (bps)", linewidth=1.5, marker='s', markersize=2, color=cor_taxa_calculada)
    if taxa_teorica or taxa_calculada:
        ax4.legend(loc='upper right', fontsize=8)
        val_min, val_max = min(taxa_teorica + taxa_calculada), max(taxa_teorica + taxa_calculada)
        margem = (val_max - val_min) * 0.10 or 5
        ax4.set_ylim(max(0, val_min - margem), val_max + margem)
    ax4.set_title("Taxa de Canal LoRa - Teórica x Real", fontsize=9); ax4.set_ylabel("Taxa (bps)", fontsize=9); ax4.tick_params(axis='both', labelsize=7)

    canvas1.draw(); canvas2.draw(); canvas3.draw(); canvas4.draw()
    raiz.after(1000, atualizar_grafico, ax1, ax2, ax3, ax4, canvas1, canvas2, canvas3, canvas4, raiz, label_down, label_up, label_snr_down, label_snr_up, label_psr, label_taxa_teorica, label_taxa_calculada)


# ===================== BOTÕES DE SALVAMENTO =====================
def salvar(fig1, fig2, fig3=None, fig4=None):
    arquivo = tkFileDialog.asksaveasfilename(defaultextension=".png")
    if arquivo:
        fig1.savefig(arquivo.replace(".png","_rssi.png"))
        fig2.savefig(arquivo.replace(".png","_snr.png"))
        if fig3 is not None: fig3.savefig(arquivo.replace(".png","_psr.png"))
        if fig4 is not None: fig4.savefig(arquivo.replace(".png","_taxa.png"))


# ===================== INTERFACE PRINCIPAL =====================
raiz = Tk()
raiz.title("FEE230 - NÍVEL 6 - GERÊNCIA LORA")
raiz.geometry("1350x980")
raiz.resizable(True, True)

try: raiz.state('zoomed')
except Exception:
    try: raiz.attributes('-zoomed', True)
    except Exception: pass

# Variável que armazenará o End Device atual escolhido pelo operador
end_device_selecionado = StringVar(value="1")

notebook = ttk.Notebook(raiz)
notebook.pack(fill=BOTH, expand=True, padx=5, pady=5)

style_ttk = ttk.Style()
style_ttk.configure("TNotebook.Tab", font=("Arial", 10, "bold"), padding=[12, 6])


# =============================================================================
# ABA 1: LoRa Site Survey
# =============================================================================
aba_gerencia = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_gerencia, text="  📡 LoRa Site Survey ")

reg_parametrizacao = Frame(master=aba_gerencia, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_parametrizacao.place(x=10, y=10, width=300, height=310)

Label(reg_parametrizacao, font=("Arial", 14, "bold"), text="Configurações LoRa", padx=5, pady=5, bg="#F0F0F0").pack(side=TOP, anchor="n")

# Seletor do End Device
Label(reg_parametrizacao, text="End Device (Nó Sensor):", font=("Arial", 11, "bold"), bg="#F0F0F0").place(x=20, y=50)
lista_ids = [str(dev) for dev in ler_end_devices()]
combo_devices = ttk.Combobox(reg_parametrizacao, textvariable=end_device_selecionado, values=lista_ids, state="readonly", width=12, font=("Arial", 11))
combo_devices.place(x=20, y=80)
if lista_ids:
    combo_devices.current(0)

# Campo da Qtde. de Medidas
Label(reg_parametrizacao, text="Qtde. de Medidas", font=("Arial", 12), bg="#F0F0F0").place(x=20, y=120)
valor_intervalo = Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_intervalo.place(x=20, y=150); valor_intervalo.insert(0, "100")

status_texto_ger = StringVar(); status_texto_ger.set("LoRa Site Survey - COMANDO PARADO")
label_status_ger = Label(reg_parametrizacao, textvariable=status_texto_ger, font=("Arial", 10, "bold"), fg="red", bg="#F0F0F0")
label_status_ger.place(x=15, y=250)

status_texto_ger2 = StringVar(); status_texto_ger2.set("LoRa Site Survey - ESTADO PARADO")
label_status_ger2 = Label(reg_parametrizacao, textvariable=status_texto_ger2, font=("Arial", 10, "bold"), fg="red", bg="#F0F0F0")
label_status_ger2.place(x=15, y=275)

def captura_num_medidas(): v = valor_intervalo.get(); return int(v) if v and int(v) > 0 else 10

def grava_comandos(condicao_start):
    with open(os.path.join(dir_nivel4, 'PARAMETROS.txt'), 'w') as s:
        s.write(f"{condicao_start}\n{captura_num_medidas()}\n12\n125\n8\n20\n8\n0\n")

btn_iniciar = Button(reg_parametrizacao, text="INICIAR", font=("Arial", 12, "bold"), width=10, command=lambda: grava_comandos(1))
btn_iniciar.place(x=25, y=200)
btn_parar = Button(reg_parametrizacao, text="PARAR", font=("Arial", 12, "bold"), width=10, command=lambda: grava_comandos(0))
btn_parar.place(x=155, y=200)

reg_estatisticas = Frame(master=aba_gerencia, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_estatisticas.place(x=10, y=330, width=300, relheight=1.0, height=400)

Label(reg_estatisticas, font=("Arial", 12, "bold"), text="RSSI / SNR / PSR (DL / UL)", bg="#F0F0F0").pack(side=TOP, anchor="n", pady=(6, 4))
texto_estatisticas = Text(reg_estatisticas, font=("Consolas", 9), bg="white", fg="black", wrap="none", relief="flat", state="disabled")
texto_estatisticas.pack(side=TOP, fill="both", expand=True, padx=6, pady=(0, 6))

def _ler_ultima_linha_valida(caminho):
    try:
        with open(caminho, 'r') as f: linhas = f.readlines()
    except FileNotFoundError: return None
    for linha in reversed(linhas):
        if linha.strip(): return linha.strip()
    return None

def ler_ultimo_valor_rssi_snr():
    linha = _ler_ultima_linha_valida(get_tmp_path("rssi.tmp"))
    if not linha: return None
    try:
        partes = linha.split()
        return (float(partes[0].replace(",", ".")), float(partes[1].replace(",", ".")), float(partes[2].replace(",", ".")), float(partes[3].replace(",", ".")))
    except (ValueError, IndexError): return None

def ler_ultimo_psr():
    linha = _ler_ultima_linha_valida(get_tmp_path("psr.tmp"))
    return float(linha) if linha else None

def ler_stats_min_max():
    try:
        with open(get_tmp_path("stats.tmp"), 'r') as f:
            linha = f.readline().strip()
    except FileNotFoundError:
        return None
    if not linha:
        return None
    
    def parse_float(val):
        if not val or val == "None":
            return None
        try:
            return float(val.replace(",", "."))
        except ValueError:
            return None

    return tuple(parse_float(c) for c in linha.split()[:8])

def _fmt(valor, unidade=""):
    return ("{:.2f}".format(valor) + (" " + unidade if unidade else "")) if valor is not None else "--"


def ler_ultima_taxa_calculada():
    """Lê a última Taxa Calculada/Real processada em taxa_dados.tmp para o nó atual."""
    linha = _ler_ultima_linha_valida(get_tmp_path("taxa_dados.tmp"))
    if not linha:
        return None
    try:
        partes = linha.split()
        if len(partes) >= 2:
            val_calc = partes[1].replace(",", ".")
            if val_calc != "None":
                return float(val_calc)
    except (ValueError, IndexError):
        pass
    return None


def atualizar_texto_estatisticas():
    dados_atual = ler_ultimo_valor_rssi_snr()
    psr_atual = ler_ultimo_psr()
    stats = ler_stats_min_max()
    taxa_calc_atual = ler_ultima_taxa_calculada() # <- Chama a nova função

    rssi_dl_at, rssi_ul_at, snr_dl_at, snr_ul_at = dados_atual if dados_atual else (None,)*4
    (rssi_dl_min, rssi_dl_max, rssi_ul_min, rssi_ul_max, snr_dl_min, snr_dl_max, snr_ul_min, snr_ul_max) = stats if stats else (None,)*8

    linhas_texto = [
        "=== RSSI (dBm) ===", "Downlink:", f"  atual {_fmt(rssi_dl_at):>10}", f"  min   {_fmt(rssi_dl_min):>10}   max {_fmt(rssi_dl_max):>10}",
        "Uplink:", f"  atual {_fmt(rssi_ul_at):>10}", f"  min   {_fmt(rssi_ul_min):>10}   max {_fmt(rssi_ul_max):>10}", "",
        "=== SNR (dB) ===", "Downlink:", f"  atual {_fmt(snr_dl_at):>10}", f"  min   {_fmt(snr_dl_min):>10}   max {_fmt(snr_dl_max):>10}",
        "Uplink:", f"  atual {_fmt(snr_ul_at):>10}", f"  min   {_fmt(snr_ul_min):>10}   max {_fmt(snr_ul_max):>10}", "",
        "=== PSR atual === " f"    {_fmt(psr_atual, '%'):>10}", "",
        "=== Taxa Real atual ===" f"  {_fmt(taxa_calc_atual, 'bps'):>10}"
    ]

    texto_estatisticas.config(state="normal")
    texto_estatisticas.delete("1.0", "end")
    texto_estatisticas.insert("1.0", "\n".join(linhas_texto))
    texto_estatisticas.config(state="disabled")

    path_param = os.path.join(dir_nivel4, 'cmd_lora.txt')
    if os.path.exists(path_param):
        try:
            with open(path_param, 'r') as f: linhas = [linha.strip() for linha in f.readlines()]
            cmd_lss = linhas[0] if len(linhas) > 0 else "0"
            estado_lss = linhas[1] if len(linhas) > 0 else "0"

            mensagens_cmd = {"0": ("TESTE PARADO", "red"), "1": ("CMD CONFIG RADIO", "blue"), "3": ("CMD TESTE ENLACE", "blue"), "4": ("LSS EM ANDAMENTO", "green"), "5": ("ENVIA ÚLTIMO PKT", "green"), "10": ("CMD GATEWAY MAX", "blue")}
            if cmd_lss in mensagens_cmd:
                status_texto_ger.set(f"LoRa Site Survey - {mensagens_cmd[cmd_lss][0]}")
                label_status_ger.config(fg=mensagens_cmd[cmd_lss][1])

            mensagens_est = {"0": ("ESTADO PARADO", "red"), "1": ("ERRO CONFIG RADIO", "blue"), "3": ("RADIO CONFIGURADO", "blue"), "4": ("TESTE ENLACE OK", "blue"), "5": ("ÚLTIMO PKT UL OK", "green"), "6": ("PACOTE UL RECEBIDO", "green"), "10": ("GATEWAY MAX OK", "blue")}
            if estado_lss in mensagens_est:
                status_texto_ger2.set(f"LoRa Site Survey - {mensagens_est[estado_lss][0]}")
                label_status_ger2.config(fg=mensagens_est[estado_lss][1])
        except Exception: pass
    raiz.after(REFRESH_MS, atualizar_texto_estatisticas)

atualizar_texto_estatisticas()

reg_amostragem = Frame(master=aba_gerencia, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_amostragem.place(x=320, y=10, relwidth=1.0, width=-330, relheight=1.0, height=-20)

frame_cabecalho_amostragem = Frame(reg_amostragem, bg="#F0F0F0")
frame_cabecalho_amostragem.pack(side=TOP, fill="x", padx=8, pady=(8, 4))
Label(frame_cabecalho_amostragem, font=("Arial", 14, "bold"), text="Amostragem de Pacotes DL/UL - Teste em Andamento", bg="#F0F0F0").pack(side=TOP, anchor="w")

label_arquivo_amostragem = Label(frame_cabecalho_amostragem, text="Arquivo: -- (aguardando início de teste) --", font=("Arial", 9), fg="gray30", bg="#F0F0F0")
label_arquivo_amostragem.pack(side=TOP, anchor="w", pady=(2, 0))
label_status_amostragem = Label(frame_cabecalho_amostragem, text="Medida: --", font=("Arial", 9, "bold"), fg="gray30", bg="#F0F0F0")
label_status_amostragem.pack(side=TOP, anchor="w")

frame_tabela_amostragem = Frame(reg_amostragem, bg="#F0F0F0")
frame_tabela_amostragem.pack(side=TOP, fill="both", expand=True, padx=8, pady=(4, 8))

colunas_amostragem = ("medida", "timestamp", "dl_bytes", "ul_bytes")
tabela_pacotes = ttk.Treeview(frame_tabela_amostragem, columns=colunas_amostragem, show="headings")
tabela_pacotes.heading("medida", text="Medida"); tabela_pacotes.heading("timestamp", text="Timestamp")
tabela_pacotes.heading("dl_bytes", text="Pacote Downlink (30 bytes)"); tabela_pacotes.heading("ul_bytes", text="Pacote Uplink (30 bytes)")
tabela_pacotes.column("medida", width=60, anchor="center", stretch=False); tabela_pacotes.column("timestamp", width=160, anchor="center", stretch=False)
tabela_pacotes.column("dl_bytes", width=420, anchor="w", stretch=True); tabela_pacotes.column("ul_bytes", width=420, anchor="w", stretch=True)

scroll_v_amostragem = ttk.Scrollbar(frame_tabela_amostragem, orient="vertical", command=tabela_pacotes.yview)
scroll_h_amostragem = ttk.Scrollbar(frame_tabela_amostragem, orient="horizontal", command=tabela_pacotes.xview)
tabela_pacotes.configure(yscrollcommand=scroll_v_amostragem.set, xscrollcommand=scroll_h_amostragem.set)

tabela_pacotes.grid(row=0, column=0, sticky="nsew"); scroll_v_amostragem.grid(row=0, column=1, sticky="ns")
scroll_h_amostragem.grid(row=1, column=0, sticky="ew")
frame_tabela_amostragem.rowconfigure(0, weight=1); frame_tabela_amostragem.columnconfigure(0, weight=1)

MAX_LINHAS_TABELA = 500
arquivo_atual_amostragem, posicao_leitura_amostragem, buffer_incompleto_amostragem = None, 0, ""

def localizar_arquivo_rodada_mais_recente():
    try:
        arquivos = glob.glob(os.path.join(os.path.dirname(__file__), "../3_N4_Armazenamento/Dados_Brutos/Rodada_Teste_*.txt"))
        if arquivos: return max(arquivos, key=os.path.getmtime)
    except Exception: pass
    return None

def atualizar_amostragem_pacotes():
    global arquivo_atual_amostragem, posicao_leitura_amostragem, buffer_incompleto_amostragem
    arquivo_mais_recente = localizar_arquivo_rodada_mais_recente()
    if arquivo_mais_recente != arquivo_atual_amostragem:
        for item in tabela_pacotes.get_children(): tabela_pacotes.delete(item)
        arquivo_atual_amostragem, posicao_leitura_amostragem, buffer_incompleto_amostragem = arquivo_mais_recente, 0, ""
        label_arquivo_amostragem.config(text=f"Arquivo: {os.path.basename(arquivo_mais_recente)}" if arquivo_mais_recente else "Arquivo: -- (aguardando início de teste) --")
        label_status_amostragem.config(text="Medida: --")

    if arquivo_atual_amostragem and os.path.exists(arquivo_atual_amostragem):
        try:
            with open(arquivo_atual_amostragem, 'r') as f:
                f.seek(posicao_leitura_amostragem)
                novo_conteudo = f.read()
                posicao_leitura_amostragem = f.tell()

            ultima_medida = None
            if novo_conteudo:
                buffer_incompleto_amostragem += novo_conteudo
                linhas = buffer_incompleto_amostragem.split("\n")
                buffer_incompleto_amostragem = linhas[-1]
                linhas_completas = linhas[:-1]

                for linha in linhas_completas:
                    linha = linha.strip()
                    if not linha or linha.startswith("Time stamp"): continue
                    campos = [c.strip() for c in linha.split(",")]
                    if len(campos) < 62: continue
                    tabela_pacotes.insert("", "end", values=(campos[1], campos[0], ", ".join(campos[2:32]), ", ".join(campos[32:62])))
                    ultima_medida = campos[1]

                filhos = tabela_pacotes.get_children()
                if len(filhos) > MAX_LINHAS_TABELA:
                    for item in filhos[:len(filhos) - MAX_LINHAS_TABELA]: tabela_pacotes.delete(item)
                if linhas_completas: tabela_pacotes.yview_moveto(1.0)
            if ultima_medida is not None:
                label_status_amostragem.config(text=f"Medida: {ultima_medida} de {captura_num_medidas()}")
        except Exception: pass
    raiz.after(REFRESH_MS, atualizar_amostragem_pacotes)

atualizar_amostragem_pacotes()


# =============================================================================
# ABA 2: GERÊNCIA LoRa
# =============================================================================
aba_gerencia_completa = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_gerencia_completa, text="  📶 Gerência de Rede LoRa  ")

frame_labels_rssi = Frame(aba_gerencia_completa)
frame_labels_rssi.pack(fill="x", padx=10, pady=(10,5))
label_down = Label(frame_labels_rssi, text="RSSI DL atual: --", font=("Arial",9,"bold"), bg=cor_rssi_down, fg="white", relief="ridge", bd=3, width=20, pady=4)
label_down.pack(side="left", padx=5)
label_up = Label(frame_labels_rssi, text="RSSI UL atual: --", font=("Arial",9,"bold"), bg=cor_rssi_up, fg="white", relief="ridge", bd=3, width=20, pady=4)
label_up.pack(side="left", padx=5)

btn = Button(frame_labels_rssi, text="Salvar Gráficos", command=lambda: salvar(fig1, fig2))
btn.pack(side="right", pady=5)

frame_rssi = Frame(aba_gerencia_completa)
frame_rssi.pack(fill="both", expand=True, padx=10, pady=5)
fig1 = Figure(figsize=(10,1.8)); ax1 = fig1.add_subplot(111)
canvas1 = FigureCanvasTkAgg(fig1, master=frame_rssi)
canvas1.get_tk_widget().pack(fill="both", expand=True)

frame_labels_snr = Frame(aba_gerencia_completa)
frame_labels_snr.pack(fill="x", padx=10, pady=(10,5))
label_snr_down = Label(frame_labels_snr, text="SNR DL atual: --", font=("Arial",9,"bold"), bg=cor_snr_down, fg="white", relief="ridge", bd=3, width=20, pady=4)
label_snr_down.pack(side="left", padx=5)
label_snr_up = Label(frame_labels_snr, text="SNR UL atual: --", font=("Arial",9,"bold"), bg=cor_snr_up, fg="white", relief="ridge", bd=3, width=20, pady=4)
label_snr_up.pack(side="left", padx=5)

frame_snr = Frame(aba_gerencia_completa)
frame_snr.pack(fill="both", expand=True, padx=10, pady=5)
fig2 = Figure(figsize=(10,1.8)); ax2 = fig2.add_subplot(111)
canvas2 = FigureCanvasTkAgg(fig2, master=frame_snr)
canvas2.get_tk_widget().pack(fill="both", expand=True)


# =============================================================================
# ABA 3: TAXAS DE DADOS / PSR
# =============================================================================
aba_taxas = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_taxas, text="  📊 PSR / Taxas de Dados  ")

frame_label_psr = Frame(aba_taxas)
frame_label_psr.pack(fill="x", padx=10, pady=(10,5))
label_psr = Label(frame_label_psr, text="PSR atual: --", font=("Arial",9,"bold"), bg=cor_psr, fg="white", relief="ridge", bd=3, width=15, pady=4)
label_psr.pack(side="left", padx=5)

btn_taxas = Button(frame_label_psr, text="Salvar Gráficos", command=lambda: salvar(fig1, fig2, fig3, fig4))
btn_taxas.pack(side="right", pady=5)

frame_psr = Frame(aba_taxas)
frame_psr.pack(fill="both", expand=True, padx=10, pady=5)
fig3 = Figure(figsize=(10,1.8)); ax3 = fig3.add_subplot(111)
canvas3 = FigureCanvasTkAgg(fig3, master=frame_psr)
canvas3.get_tk_widget().pack(fill="both", expand=True)

frame_labels_taxa = Frame(aba_taxas)
frame_labels_taxa.pack(fill="x", padx=10, pady=(10,5))
label_taxa_teorica = Label(frame_labels_taxa, text="Taxa Teórica atual: --", font=("Arial",9,"bold"), bg=cor_taxa_teorica, fg="white", relief="ridge", bd=3, width=25, pady=4)
label_taxa_teorica.pack(side="left", padx=5)
label_taxa_calculada = Label(frame_labels_taxa, text="Taxa Real atual: --", font=("Arial",9,"bold"), bg=cor_taxa_calculada, fg="white", relief="ridge", bd=3, width=25, pady=4)
label_taxa_calculada.pack(side="left", padx=5)

frame_taxa = Frame(aba_taxas)
frame_taxa.pack(fill="both", expand=True, padx=10, pady=5)
fig4 = Figure(figsize=(10,1.8)); ax4 = fig4.add_subplot(111)
canvas4 = FigureCanvasTkAgg(fig4, master=frame_taxa)
canvas4.get_tk_widget().pack(fill="both", expand=True)

atualizar_grafico(ax1, ax2, ax3, ax4, canvas1, canvas2, canvas3, canvas4, raiz, label_down, label_up, label_snr_down, label_snr_up, label_psr, label_taxa_teorica, label_taxa_calculada)


# =============================================================================
# ABA 4: GPS & DISTÂNCIA
# =============================================================================
class VisualizadorGPS:
    def __init__(self, notebook, raiz):
        self.root = raiz
        self.node_lat, self.node_lon, self.node_alt, self.distancia = None, None, None, None

        self.tab_gps = ttk.Frame(notebook)
        notebook.add(self.tab_gps, text="  📍 GPS & Distância  ")

        self.criar_widgets_tab_gps()
        self.carregar_dados_gateway_iniciais()
        self.atualizar_dados_loop()

    def criar_widgets_tab_gps(self):
        frame_gw = ttk.LabelFrame(self.tab_gps, text=" Configuração do Gateway Fixo ", padding=10)
        frame_gw.pack(fill="x", padx=15, pady=8)
        grid_gw = ttk.Frame(frame_gw); grid_gw.pack(fill="x")
        
        ttk.Label(grid_gw, text="Latitude:").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_gw_lat = ttk.Entry(grid_gw, width=22); self.entry_gw_lat.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(grid_gw, text="Longitude:").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_gw_lon = ttk.Entry(grid_gw, width=22); self.entry_gw_lon.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(grid_gw, text="Altitude (m):").grid(row=2, column=0, sticky="w", pady=2)
        self.entry_gw_alt = ttk.Entry(grid_gw, width=22); self.entry_gw_alt.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        ttk.Button(frame_gw, text="💾 Salvar Gateway", command=self.salvar_gateway).pack(anchor="e", pady=(8, 0))

        frame_node = ttk.LabelFrame(self.tab_gps, text=" Nó Sensor (Calculado) ", padding=10)
        frame_node.pack(fill="x", padx=15, pady=8)
        self.lbl_node_lat = ttk.Label(frame_node, text="Latitude: --"); self.lbl_node_lat.pack(anchor="w")
        self.lbl_node_lon = ttk.Label(frame_node, text="Longitude: --"); self.lbl_node_lon.pack(anchor="w")
        self.lbl_node_alt = ttk.Label(frame_node, text="Altitude: --"); self.lbl_node_alt.pack(anchor="w")

        frame_dist = ttk.Frame(self.tab_gps, padding=5)
        frame_dist.pack(fill="x", padx=15, pady=5)
        self.lbl_distancia = ttk.Label(frame_dist, text="Distância de Enlace: --", font=("Arial", 11, "bold"), foreground="#0055A5")
        self.lbl_distancia.pack(anchor="center")

        frame_botoes = ttk.Frame(self.tab_gps, padding=10)
        frame_botoes.pack(fill="x", padx=15)
        ttk.Button(frame_botoes, text="🗺️ Abrir no Google Maps", command=self.abrir_maps).pack(side="left", expand=True, fill="x", padx=5)
        ttk.Button(frame_botoes, text="🔄 Recarregar Dados", command=self.recarregar_tudo).pack(side="right", expand=True, fill="x", padx=5)

    def carregar_dados_gateway_iniciais(self):
        gw_lat, gw_lon, gw_alt = ler_gateway_gps()
        self.entry_gw_lat.delete(0, END); self.entry_gw_lat.insert(0, f"{gw_lat:.6f}")
        self.entry_gw_lon.delete(0, END); self.entry_gw_lon.insert(0, f"{gw_lon:.6f}")
        self.entry_gw_alt.delete(0, END); self.entry_gw_alt.insert(0, f"{gw_alt:.1f}")

    def salvar_gateway(self):
        try:
            lat = float(self.entry_gw_lat.get().strip().replace(",", "."))
            lon = float(self.entry_gw_lon.get().strip().replace(",", "."))
            alt = float(self.entry_gw_alt.get().strip().replace(",", "."))
            os.makedirs(dir_nivel4, exist_ok=True)
            with open(arquivo_gw_gps, "w") as f:
                f.write(f"GW_LAT = {lat:.6f}\nGW_LON = {lon:.6f}\nGW_ALT = {alt:.1f}\n")
            messagebox.showinfo("Sucesso", f"Coordenadas do Gateway salvas em:\n{arquivo_gw_gps}")
        except ValueError:
            messagebox.showerror("Erro de Validação", "Insira valores numéricos válidos.")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível gravar o arquivo:\n{e}")

    def atualizar_dados_loop(self):
        dados_node = ler_ultimo_gps()
        if dados_node:
            self.node_lat, self.node_lon, self.node_alt = dados_node[0:3]
            self.distancia = dados_node[3] if len(dados_node) > 3 else None
            self.lbl_node_lat.config(text=f"Latitude: {self.node_lat:.6f}°")
            self.lbl_node_lon.config(text=f"Longitude: {self.node_lon:.6f}°")
            self.lbl_node_alt.config(text=f"Altitude: {self.node_alt:.1f} m")
            self.lbl_distancia.config(text=f"Distância de Enlace: {self.distancia:.2f} m" if self.distancia is not None else "Distância de Enlace: N/A")
        else:
            self.lbl_distancia.config(text="Aguardando dados de 'gps.tmp'...")
        self.root.after(2000, self.atualizar_dados_loop)

    def recarregar_tudo(self):
        self.carregar_dados_gateway_iniciais(); self.atualizar_dados_loop()

    def abrir_maps(self):
        try:
            gw_lat, gw_lon = float(self.entry_gw_lat.get().replace(",", ".")), float(self.entry_gw_lon.get().replace(",", "."))
            if self.node_lat is None or self.node_lon is None:
                messagebox.showwarning("Aviso", "Nó Sensor sem coordenadas no arquivo gps.tmp.")
                return
            webbrowser.open(f"https://www.google.com/maps/dir/?api=1&origin={gw_lat},{gw_lon}&destination={self.node_lat},{self.node_lon}")
        except ValueError:
            messagebox.showwarning("Aviso", "Coordenadas inválidas.")

app_gps = VisualizadorGPS(notebook, raiz)


# =============================================================================
# ABA 5: CADASTRO DE END DEVICES
# =============================================================================
aba_end_devices = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_end_devices, text="  💻 Nó Sensores (End Devices)  ")

# FRAME ESQUERDO: Tabela (Lista de Dispositivos)
frame_tabela_ed = Frame(aba_end_devices, bg="#F0F0F0")
frame_tabela_ed.pack(side=LEFT, fill=BOTH, expand=True, padx=20, pady=20)

Label(frame_tabela_ed, text="End Devices Cadastrados no CSV", font=("Arial", 14, "bold"), bg="#F0F0F0").pack(pady=(0, 10))

colunas_ed = ("endereco_rede", "spreading_factor", "bandwidth", "coding_rate", "potencia_tx")
tabela_ed = ttk.Treeview(frame_tabela_ed, columns=colunas_ed, show="headings", height=20)

tabela_ed.heading("endereco_rede", text="ID da Rede")
tabela_ed.heading("spreading_factor", text="Spreading Factor (SF)")
tabela_ed.heading("bandwidth", text="Bandwidth (BW)")
tabela_ed.heading("coding_rate", text="Coding Rate (CR)")
tabela_ed.heading("potencia_tx", text="Potência TX")

for col in colunas_ed:
    tabela_ed.column(col, anchor="center", width=120)

tabela_ed.pack(side=LEFT, fill=BOTH, expand=True)

scroll_ed = ttk.Scrollbar(frame_tabela_ed, orient="vertical", command=tabela_ed.yview)
tabela_ed.configure(yscrollcommand=scroll_ed.set)
scroll_ed.pack(side=RIGHT, fill=Y)

# FRAME DIREITO: Controles
frame_controles_ed = Frame(aba_end_devices, bg="#F0F0F0", width=350)
frame_controles_ed.pack(side=RIGHT, fill=Y, padx=20, pady=20)

Label(frame_controles_ed, text="Gerenciar End Devices", font=("Arial", 14, "bold"), bg="#F0F0F0").pack(pady=(0, 15))

def criar_campo(texto):
    Label(frame_controles_ed, text=texto, bg="#F0F0F0", font=("Arial", 10, "bold")).pack(anchor="w", pady=(5, 0))
    entry = Entry(frame_controles_ed, font=("Arial", 11))
    entry.pack(fill=X, pady=(0, 5))
    return entry

entry_ed_id  = criar_campo("Endereço de Rede (ID): *")
entry_ed_sf  = criar_campo("Spreading Factor (SF):")
entry_ed_bw  = criar_campo("Bandwidth (BW):")
entry_ed_cr  = criar_campo("Coding Rate (CR):")
entry_ed_ptx = criar_campo("Potência TX:")

def carregar_tabela_ed():
    for item in tabela_ed.get_children():
        tabela_ed.delete(item)
        
    if os.path.exists(arquivo_csv_end_devices):
        try:
            df_devices = pd.read_csv(arquivo_csv_end_devices)
            
            for col in colunas_ed:
                if col not in df_devices.columns:
                    df_devices[col] = ""

            for _, row in df_devices.iterrows():
                tabela_ed.insert("", "end", values=(
                    row["endereco_rede"],
                    row["spreading_factor"],
                    row["bandwidth"],
                    row["coding_rate"],
                    row["potencia_tx"]
                ))
        except Exception as e:
            print(f"Erro ao carregar CSV na tabela: {e}")

def adicionar_ed():
    novo_id = entry_ed_id.get().strip()
    sf = entry_ed_sf.get().strip()
    bw = entry_ed_bw.get().strip()
    cr = entry_ed_cr.get().strip()
    ptx = entry_ed_ptx.get().strip()

    if novo_id:
        tabela_ed.insert("", "end", values=(novo_id, sf, bw, cr, ptx))
        for entry in (entry_ed_id, entry_ed_sf, entry_ed_bw, entry_ed_cr, entry_ed_ptx):
            entry.delete(0, END)
    else:
        messagebox.showwarning("Aviso", "O Endereço de Rede (ID) é obrigatório.")

def excluir_ed():
    selecionados = tabela_ed.selection()
    if not selecionados:
        messagebox.showwarning("Aviso", "Selecione um End Device na tabela para excluir.")
        return
    for item in selecionados:
        tabela_ed.delete(item)

def salvar_ed():
    dados_para_salvar = []
    
    for item in tabela_ed.get_children():
        valores = tabela_ed.item(item, 'values')
        dados_para_salvar.append({
            "endereco_rede": valores[0],
            "spreading_factor": valores[1],
            "bandwidth": valores[2],
            "coding_rate": valores[3],
            "potencia_tx": valores[4]
        })
    
    df_salvar = pd.DataFrame(dados_para_salvar, columns=colunas_ed)
    
    try:
        df_salvar.to_csv(arquivo_csv_end_devices, index=False)
        messagebox.showinfo("Sucesso", f"End Devices salvos com sucesso em:\n{arquivo_csv_end_devices}")
        
        lista_atualizada = [str(dev) for dev in ler_end_devices()]
        combo_devices['values'] = lista_atualizada
        if lista_atualizada and end_device_selecionado.get() not in lista_atualizada:
            combo_devices.current(0)
            
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao salvar arquivo CSV: {e}")

Label(frame_controles_ed, text="", bg="#F0F0F0").pack(pady=5)

Button(frame_controles_ed, text="➕ Adicionar à Lista", font=("Arial", 11), command=adicionar_ed).pack(fill=X, pady=5)
Button(frame_controles_ed, text="❌ Excluir Selecionado", font=("Arial", 11), command=excluir_ed).pack(fill=X, pady=5)

Label(frame_controles_ed, text="----------------------------------------", bg="#F0F0F0", fg="gray").pack(pady=10)

Button(frame_controles_ed, text="💾 Salvar Alterações no Arquivo", font=("Arial", 11, "bold"), bg="#4CAF50", fg="white", command=salvar_ed).pack(fill=X, pady=10)

carregar_tabela_ed()

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
