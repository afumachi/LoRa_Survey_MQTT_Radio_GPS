import os
import re
import sys
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

# Diretores de Parâmetros e Dados Processados (Nível 4)
dir_nivel4 = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../3_N4_Armazenamento/Parametros/",
)
arquivo_gw_gps = os.path.join(dir_nivel4, "gateway_gps.txt")
arquivo_param_prop = os.path.join(dir_nivel4, "parametros_propagacao.txt")

dir_dados = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../3_N4_Armazenamento/Dados_Processados/",
)
arquivo_gps_tmp = os.path.join(dir_dados, "gps.tmp")
arquivo_prop_tmp = os.path.join(dir_dados, "propagacao.tmp")

# Valores de fallback padrão - GPS
GW_LAT_DEFAULT = -23.005380
GW_LON_DEFAULT = -46.835336
GW_ALT_DEFAULT = 770.0

# Valores padrão do Modelo de Propagação (segundo tabela)
P_TX_DEFAULT = 17.0
G_TX_DEFAULT = 0.0
G_RX_DEFAULT = 0.0
C_DEFAULT = 299792458.0
F_DEFAULT = 903000000.0
S_RX_DEFAULT = -136.0


def ler_gateway_gps():
    """Lê as coordenadas do Gateway a partir do arquivo gateway_gps.txt."""
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

            floats = [
                float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", conteudo)
            ]
            if len(floats) >= 3:
                gw_lat, gw_lon, gw_alt = floats[0], floats[1], floats[2]
            elif len(floats) == 2:
                gw_lat, gw_lon = floats[0], floats[1]

        except Exception as e:
            print(f"Erro ao ler {arquivo_gw_gps}: {e}")

    return gw_lat, gw_lon, gw_alt


def ler_ultimo_gps():
    """Lê a última linha do arquivo gps.tmp."""
    caminho_arquivo = arquivo_gps_tmp
    if not os.path.exists(caminho_arquivo) and os.path.exists("gps.tmp"):
        caminho_arquivo = "gps.tmp"

    if not os.path.exists(caminho_arquivo):
        return None

    try:
        with open(caminho_arquivo, "r") as f:
            linhas = [line.strip() for line in f if line.strip()]
            if not linhas:
                return None

            partes = linhas[-1].split()
            if len(partes) >= 4:
                return (
                    float(partes[0]),
                    float(partes[1]),
                    float(partes[2]),
                    float(partes[3]),
                )
            elif len(partes) == 3:
                return float(partes[0]), float(partes[1]), float(partes[2]), None
    except Exception as e:
        print(f"Erro ao ler o arquivo {caminho_arquivo}: {e}")
        return None


def ler_parametros_propagacao():
    """Lê os parâmetros salvos no arquivo parametros_propagacao.txt."""
    params = {
        "P_TX": P_TX_DEFAULT,
        "G_TX": G_TX_DEFAULT,
        "G_RX": G_RX_DEFAULT,
        "C": C_DEFAULT,
        "F": F_DEFAULT,
        "S_RX": S_RX_DEFAULT,
    }

    if os.path.exists(arquivo_param_prop):
        try:
            with open(arquivo_param_prop, "r") as f:
                for linha in f:
                    if "=" in linha and not linha.strip().startswith("#"):
                        chave, val = linha.split("=", 1)
                        chave_clean = chave.strip().upper()
                        try:
                            params[chave_clean] = float(val.strip())
                        except ValueError:
                            pass
        except Exception as e:
            print(f"Erro ao ler {arquivo_param_prop}: {e}")

    return params


def ler_resultado_propagacao():
    """Lê o valor calculado de P_Rx do arquivo temporário propagacao.tmp."""
    if not os.path.exists(arquivo_prop_tmp):
        return None

    try:
        with open(arquivo_prop_tmp, "r") as f:
            linhas = [line.strip() for line in f if line.strip()]
            if linhas:
                return linhas[-1]
    except Exception as e:
        print(f"Erro ao ler {arquivo_prop_tmp}: {e}")

    return None


class VisualizadorGPS:

    def __init__(self, root):
        self.root = root
        self.root.title("Monitor de Enlace LoRa & Modelo de Propagação")
        self.root.geometry("500x520")
        self.root.resizable(False, False)

        self.node_lat = None
        self.node_lon = None
        self.node_alt = None
        self.distancia = None

        # Container Principal com Abas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.tab_gps = ttk.Frame(self.notebook)
        self.tab_prop = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_gps, text="📍 GPS & Distância")
        self.notebook.add(self.tab_prop, text="📡 Propagação Espaço Livre")

        # Construção da Interface das Abas
        self.criar_widgets_tab_gps()
        self.criar_widgets_tab_prop()

        # Inicialização de dados
        self.carregar_dados_gateway_iniciais()
        self.carregar_parametros_propagacao_iniciais()
        self.atualizar_dados_loop()

    # ------------------ ABA 1: GPS & DISTÂNCIA ------------------
    def criar_widgets_tab_gps(self):
        # Frame Gateway Fixo
        frame_gw = ttk.LabelFrame(
            self.tab_gps, text=" Configuração do Gateway Fixo ", padding=10
        )
        frame_gw.pack(fill="x", padx=15, pady=8)

        grid_gw = ttk.Frame(frame_gw)
        grid_gw.pack(fill="x")

        ttk.Label(grid_gw, text="Latitude:").grid(
            row=0, column=0, sticky="w", pady=2
        )
        self.entry_gw_lat = ttk.Entry(grid_gw, width=22)
        self.entry_gw_lat.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(grid_gw, text="Longitude:").grid(
            row=1, column=0, sticky="w", pady=2
        )
        self.entry_gw_lon = ttk.Entry(grid_gw, width=22)
        self.entry_gw_lon.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(grid_gw, text="Altitude (m):").grid(
            row=2, column=0, sticky="w", pady=2
        )
        self.entry_gw_alt = ttk.Entry(grid_gw, width=22)
        self.entry_gw_alt.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        btn_salvar_gw = ttk.Button(
            frame_gw, text="💾 Salvar Gateway", command=self.salvar_gateway
        )
        btn_salvar_gw.pack(anchor="e", pady=(8, 0))

        # Frame Nó Sensor
        frame_node = ttk.LabelFrame(
            self.tab_gps, text=" Nó Sensor (Calculado) ", padding=10
        )
        frame_node.pack(fill="x", padx=15, pady=8)

        self.lbl_node_lat = ttk.Label(frame_node, text="Latitude: --")
        self.lbl_node_lat.pack(anchor="w")
        self.lbl_node_lon = ttk.Label(frame_node, text="Longitude: --")
        self.lbl_node_lon.pack(anchor="w")
        self.lbl_node_alt = ttk.Label(frame_node, text="Altitude: --")
        self.lbl_node_alt.pack(anchor="w")

        # Frame Distância
        frame_dist = ttk.Frame(self.tab_gps, padding=5)
        frame_dist.pack(fill="x", padx=15, pady=5)

        self.lbl_distancia = ttk.Label(
            frame_dist,
            text="Distância de Enlace: --",
            font=("Arial", 11, "bold"),
            foreground="#0055A5",
        )
        self.lbl_distancia.pack(anchor="center")

        # Botões Inferiores
        frame_botoes = ttk.Frame(self.tab_gps, padding=10)
        frame_botoes.pack(fill="x", padx=15)

        btn_maps = ttk.Button(
            frame_botoes, text="🗺️ Abrir no Google Maps", command=self.abrir_maps
        )
        btn_maps.pack(side="left", expand=True, fill="x", padx=5)

        btn_refresh = ttk.Button(
            frame_botoes, text="🔄 Recarregar Dados", command=self.recarregar_tudo
        )
        btn_refresh.pack(side="right", expand=True, fill="x", padx=5)

    # ------------------ ABA 2: PROPAGAÇÃO ESPAÇO LIVRE ------------------
    def criar_widgets_tab_prop(self):
        frame_params = ttk.LabelFrame(
            self.tab_prop,
            text=" Parâmetros do Modelo de Espaço Livre ",
            padding=10,
        )
        frame_params.pack(fill="x", padx=15, pady=8)

        grid_prop = ttk.Frame(frame_params)
        grid_prop.pack(fill="x")

        # Potência TX (P_TX)
        ttk.Label(grid_prop, text="Potência TX (P_TX):").grid(
            row=0, column=0, sticky="w", pady=3
        )
        self.entry_ptx = ttk.Entry(grid_prop, width=15)
        self.entry_ptx.grid(row=0, column=1, sticky="w", padx=5, pady=3)
        ttk.Label(grid_prop, text="dBm").grid(
            row=0, column=2, sticky="w", pady=3
        )

        # Ganho Antena TX (G_TX)
        ttk.Label(grid_prop, text="Ganho Antena TX (G_TX):").grid(
            row=1, column=0, sticky="w", pady=3
        )
        self.entry_gtx = ttk.Entry(grid_prop, width=15)
        self.entry_gtx.grid(row=1, column=1, sticky="w", padx=5, pady=3)
        ttk.Label(grid_prop, text="dBi").grid(
            row=1, column=2, sticky="w", pady=3
        )

        # Ganho Antena RX (G_RX)
        ttk.Label(grid_prop, text="Ganho Antena RX (G_RX):").grid(
            row=2, column=0, sticky="w", pady=3
        )
        self.entry_grx = ttk.Entry(grid_prop, width=15)
        self.entry_grx.grid(row=2, column=1, sticky="w", padx=5, pady=3)
        ttk.Label(grid_prop, text="dBi").grid(
            row=2, column=2, sticky="w", pady=3
        )

        # Velocidade da Luz (c)
        ttk.Label(grid_prop, text="Velocidade da luz (c):").grid(
            row=3, column=0, sticky="w", pady=3
        )
        self.entry_c = ttk.Entry(grid_prop, width=15)
        self.entry_c.grid(row=3, column=1, sticky="w", padx=5, pady=3)
        ttk.Label(grid_prop, text="m/s").grid(
            row=3, column=2, sticky="w", pady=3
        )

        # Frequência de operação (f)
        ttk.Label(grid_prop, text="Frequência operação (f):").grid(
            row=4, column=0, sticky="w", pady=3
        )
        self.entry_f = ttk.Entry(grid_prop, width=15)
        self.entry_f.grid(row=4, column=1, sticky="w", padx=5, pady=3)
        ttk.Label(grid_prop, text="Hz").grid(
            row=4, column=2, sticky="w", pady=3
        )

        # Comprimento de Onda (lambda)
        ttk.Label(grid_prop, text="Comprimento de onda (λ):").grid(
            row=5, column=0, sticky="w", pady=3
        )
        self.lbl_lambda_val = ttk.Label(
            grid_prop, text="-- m", font=("Arial", 9, "bold")
        )
        self.lbl_lambda_val.grid(row=5, column=1, sticky="w", padx=5, pady=3)

        # Sensibilidade RX (S_RX)
        ttk.Label(grid_prop, text="Sensibilidade Rx (S_RX):").grid(
            row=6, column=0, sticky="w", pady=3
        )
        self.entry_srx = ttk.Entry(grid_prop, width=15)
        self.entry_srx.grid(row=6, column=1, sticky="w", padx=5, pady=3)
        ttk.Label(grid_prop, text="dBm").grid(
            row=6, column=2, sticky="w", pady=3
        )

        # Vincular atualização automática do comprimento de onda (lambda)
        self.entry_c.bind("<KeyRelease>", self.atualizar_lambda_display)
        self.entry_f.bind("<KeyRelease>", self.atualizar_lambda_display)

        # Botão Principal de Cálculo
        btn_calc_prx = ttk.Button(
            self.tab_prop,
            text="⚡ Calcular P_Rx EL",
            command=self.calcular_p_rx_el,
        )
        btn_calc_prx.pack(fill="x", padx=15, pady=10)

        # Frame Resultados
        frame_resultado = ttk.LabelFrame(
            self.tab_prop, text=" Resultado do Modelo (propagacao.tmp) ", padding=10
        )
        frame_resultado.pack(fill="x", padx=15, pady=5)

        self.lbl_prx_resultado = ttk.Label(
            frame_resultado,
            text="P_Rx Calculado: Aguardando execução...",
            font=("Arial", 11, "bold"),
            foreground="#008000",
        )
        self.lbl_prx_resultado.pack(anchor="center", pady=5)

    # ------------------ FUNÇÕES LÓGICAS E MANIPULAÇÃO ------------------
    def carregar_dados_gateway_iniciais(self):
        gw_lat, gw_lon, gw_alt = ler_gateway_gps()
        self.entry_gw_lat.delete(0, tk.END)
        self.entry_gw_lat.insert(0, f"{gw_lat:.6f}")
        self.entry_gw_lon.delete(0, tk.END)
        self.entry_gw_lon.insert(0, f"{gw_lon:.6f}")
        self.entry_gw_alt.delete(0, tk.END)
        self.entry_gw_alt.insert(0, f"{gw_alt:.1f}")

    def carregar_parametros_propagacao_iniciais(self):
        params = ler_parametros_propagacao()
        self.entry_ptx.delete(0, tk.END)
        self.entry_ptx.insert(0, str(params["P_TX"]))
        self.entry_gtx.delete(0, tk.END)
        self.entry_gtx.insert(0, str(params["G_TX"]))
        self.entry_grx.delete(0, tk.END)
        self.entry_grx.insert(0, str(params["G_RX"]))
        self.entry_c.delete(0, tk.END)
        self.entry_c.insert(0, str(int(params["C"])))
        self.entry_f.delete(0, tk.END)
        self.entry_f.insert(0, str(int(params["F"])))
        self.entry_srx.delete(0, tk.END)
        self.entry_srx.insert(0, str(params["S_RX"]))

        self.atualizar_lambda_display()

    def atualizar_lambda_display(self, event=None):
        try:
            c = float(self.entry_c.get().strip().replace(",", "."))
            f = float(self.entry_f.get().strip().replace(",", "."))
            if f > 0:
                lmbda = c / f
                self.lbl_lambda_val.config(text=f"{lmbda:.7f} m")
            else:
                self.lbl_lambda_val.config(text="Erro (f=0)")
        except ValueError:
            self.lbl_lambda_val.config(text="-- m")

    def salvar_gateway(self):
        try:
            lat = float(self.entry_gw_lat.get().strip().replace(",", "."))
            lon = float(self.entry_gw_lon.get().strip().replace(",", "."))
            alt = float(self.entry_gw_alt.get().strip().replace(",", "."))
        except ValueError:
            messagebox.showerror(
                "Erro de Validação",
                "Insira valores numéricos válidos para Latitude, Longitude e Altitude.",
            )
            return

        os.makedirs(dir_nivel4, exist_ok=True)
        try:
            with open(arquivo_gw_gps, "w") as f:
                f.write(f"GW_LAT = {lat:.6f}\n")
                f.write(f"GW_LON = {lon:.6f}\n")
                f.write(f"GW_ALT = {alt:.1f}\n")

            messagebox.showinfo(
                "Sucesso",
                f"Coordenadas do Gateway salvas com sucesso em:\n{arquivo_gw_gps}",
            )
        except Exception as e:
            messagebox.showerror(
                "Erro ao Salvar", f"Não foi possível gravar o arquivo:\n{e}"
            )

    def calcular_p_rx_el(self):
        """Salva os parâmetros num arquivo txt de nome parametros_propagacao.txt."""
        try:
            p_tx = float(self.entry_ptx.get().strip().replace(",", "."))
            g_tx = float(self.entry_gtx.get().strip().replace(",", "."))
            g_rx = float(self.entry_grx.get().strip().replace(",", "."))
            c = float(self.entry_c.get().strip().replace(",", "."))
            f = float(self.entry_f.get().strip().replace(",", "."))
            s_rx = float(self.entry_srx.get().strip().replace(",", "."))

            if f <= 0:
                raise ValueError("A frequência de operação deve ser maior que zero.")

            lmbda = c / f
        except ValueError as ve:
            messagebox.showerror(
                "Erro de Validação",
                f"Verifique os parâmetros inseridos:\n{ve}",
            )
            return

        os.makedirs(dir_nivel4, exist_ok=True)

        try:
            with open(arquivo_param_prop, "w") as txt:
                txt.write(f"P_TX = {p_tx}\n")
                txt.write(f"G_TX = {g_tx}\n")
                txt.write(f"G_RX = {g_rx}\n")
                txt.write(f"C = {c}\n")
                txt.write(f"F = {f}\n")
                txt.write(f"LAMBDA = {lmbda:.7f}\n")
                txt.write(f"S_RX = {s_rx}\n")

            messagebox.showinfo(
                "Sucesso",
                f"Parâmetros salvos com sucesso em:\n{arquivo_param_prop}",
            )
            self.atualizar_resultado_propagacao()
        except Exception as e:
            messagebox.showerror(
                "Erro ao Salvar", f"Não foi possível salvar o arquivo:\n{e}"
            )

    def atualizar_dados_loop(self):
        """Atualização periódica dos arquivos .tmp (gps.tmp e propagacao.tmp)."""
        dados_node = ler_ultimo_gps()
        if dados_node:
            self.node_lat, self.node_lon, self.node_alt = (
                dados_node[0],
                dados_node[1],
                dados_node[2],
            )
            self.distancia = dados_node[3] if len(dados_node) > 3 else None

            self.lbl_node_lat.config(text=f"Latitude: {self.node_lat:.6f}°")
            self.lbl_node_lon.config(text=f"Longitude: {self.node_lon:.6f}°")
            self.lbl_node_alt.config(text=f"Altitude: {self.node_alt:.1f} m")

            if self.distancia is not None:
                self.lbl_distancia.config(
                    text=f"Distância de Enlace: {self.distancia:.2f} m"
                )
            else:
                self.lbl_distancia.config(text="Distância de Enlace: N/A")
        else:
            self.lbl_distancia.config(text="Aguardando dados de 'gps.tmp'...")

        self.atualizar_resultado_propagacao()
        self.root.after(2000, self.atualizar_dados_loop)

    def atualizar_resultado_propagacao(self):
        res = ler_resultado_propagacao()
        if res:
            self.lbl_prx_resultado.config(text=f"P_Rx Calculado: {res}")
        else:
            self.lbl_prx_resultado.config(
                text="Aguardando resultado em 'propagacao.tmp'..."
            )

    def recarregar_tudo(self):
        self.carregar_dados_gateway_iniciais()
        self.carregar_parametros_propagacao_iniciais()
        self.atualizar_dados_loop()

    def abrir_maps(self):
        try:
            gw_lat = float(self.entry_gw_lat.get().strip().replace(",", "."))
            gw_lon = float(self.entry_gw_lon.get().strip().replace(",", "."))
        except ValueError:
            messagebox.showwarning(
                "Aviso", "Coordenadas do Gateway inválidas na caixa de texto."
            )
            return

        if self.node_lat is None or self.node_lon is None:
            messagebox.showwarning(
                "Aviso",
                "Ainda não existem coordenadas válidas do Nó Sensor no arquivo gps.tmp.",
            )
            return

        url = f"https://www.google.com/maps/dir/?api=1&origin={gw_lat},{gw_lon}&destination={self.node_lat},{self.node_lon}"
        webbrowser.open(url)


if __name__ == "__main__":
    root = tk.Tk()
    app = VisualizadorGPS(root)
    root.mainloop()

