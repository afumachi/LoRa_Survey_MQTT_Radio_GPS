# FEE247 - Desenvolvimento de Soluções IoT com LoRa e LoRaWAN
# ======= Nível 5 - Gerência ============
# Extrai RSSI, SNR, PSR, GPS e estatísticas separadamente por End Device.

import math
import os
import re
import struct
import time
import pandas as pd

# Diretórios de Parâmetros e Dados Processados (Nível 4)
dir_nivel4 = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../3_N4_Armazenamento/Parametros/",
)
arquivo_gw_gps = os.path.join(dir_nivel4, "gateway_gps.txt")
arquivo_csv_end_devices = os.path.join(dir_nivel4, "end_devices_net_par.csv")

# Caminho da pasta de destino dos dados processados
pasta_dados_processados = os.path.join(
    "..", "3_N4_Armazenamento", "Dados_Processados"
)

# Garante que a pasta de destino existe
os.makedirs(pasta_dados_processados, exist_ok=True)

# MAPAS DE CONFIGURAÇÃO DE RÁDIO
MAPA_BANDWIDTH = {1: 125, 2: 250, 3: 500}
MAPA_CODINGRATE = {5: 1, 6: 2, 7: 3, 8: 4}

TAMANHO_PACOTE = 30


def ler_end_devices():
    """Lê a lista de endereços de rede dos End Devices cadastrados no CSV."""
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
            print(f"[ERRO] Falha ao ler {arquivo_csv_end_devices}: {e}")
    
    # Caso o arquivo não exista ou esteja vazio, assume lista padrão com ID 1
    if not end_devices:
        end_devices = [1]
    return sorted(list(set(end_devices)))


def ler_gateway_gps():
    """Lê as coordenadas do Gateway a partir do arquivo gateway_gps.txt."""
    gw_lat, gw_lon, gw_alt = -23.005380, -46.835336, 770.0

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
            print(f"Erro ao ler arquivo de parâmetros do Gateway: {e}")

    return gw_lat, gw_lon, gw_alt


def calcula_toa_taxa_canal(
    spreading_factor,
    bandwidth_khz,
    coding_rate,
    tamanho_pacote=TAMANHO_PACOTE,
    n_preambulo=8,
    header_impl=False,
    crc_on=True,
    low_dr_opt=None,
):
    bandwidth_hz = bandwidth_khz * 1000
    tempo_simbolo = (2**spreading_factor) / bandwidth_hz

    tempo_preambulo = (n_preambulo + 4.25) * tempo_simbolo

    if low_dr_opt is None:
        low_dr_opt = 1 if tempo_simbolo > 0.016 else 0

    valor_cr = coding_rate

    ih = 1 if header_impl else 0
    crc = 1 if crc_on else 0
    de = 1 if low_dr_opt else 0

    n_pacote = (
        8 * tamanho_pacote - 4 * spreading_factor + 28 + 16 * crc - 20 * ih
    ) / (4 * (spreading_factor - 2 * de))
    n_payload_simbolo = 8 + max(math.ceil(n_pacote) * (valor_cr + 4), 0)

    tempo_pacote_toa = n_payload_simbolo * tempo_simbolo
    toa_s = tempo_preambulo + tempo_pacote_toa
    toa_ms = toa_s * 1000

    cr = 4 / (4 + valor_cr)
    taxa_teorica = (
        spreading_factor * (bandwidth_hz / (2**spreading_factor)) * cr
    )

    return toa_ms, round(taxa_teorica, 3)


def calcula_taxa_canal(
    spreading_factor, bandwidth_khz, coding_rate, psr_percentual
):
    _, taxa_teorica = calcula_toa_taxa_canal(
        spreading_factor, bandwidth_khz, coding_rate
    )
    taxa_calculada = round((taxa_teorica * psr_percentual) / 100, 3)
    return taxa_teorica, taxa_calculada


def calcula_distancia_enlace(lat1, lon1, alt1, lat2, lon2, alt2):
    """Calcula a distância 3D em metros entre duas coordenadas geográficas."""
    if None in (lat1, lon1, alt1, lat2, lon2, alt2):
        return None

    R = 6371000.0  # Raio médio da Terra em metros
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    dist_2d = R * c

    dalt = alt2 - alt1
    dist_3d = math.sqrt(dist_2d**2 + dalt**2)

    return round(dist_3d, 2)


# Pasta de dados brutos
PASTA_ARMAZENAMENTO = os.path.join("..", "3_N4_Armazenamento")
pasta_dados_brutos = os.path.join(PASTA_ARMAZENAMENTO, "Dados_Brutos")

while True:
    try:
        # Lê dinamicamente os parâmetros do Gateway e End Devices cadastrados
        GW_LAT, GW_LON, GW_ALT = ler_gateway_gps()
        lista_end_devices = ler_end_devices()

        arquivo_entrada = ""
        if os.path.exists(pasta_dados_brutos):
            arquivos = os.listdir(pasta_dados_brutos)
            arquivos.sort()
            for nome in arquivos:
                if nome.endswith(".txt"):
                    arquivo_entrada = os.path.join(pasta_dados_brutos, nome)

        if not arquivo_entrada:
            time.sleep(1)
            continue

        try:
            with open(arquivo_entrada, "r") as arquivo:
                linhas = arquivo.readlines()
        except (FileNotFoundError, PermissionError):
            time.sleep(1)
            continue

        # Inicializa dicionários organizados por ID do End Device
        dados_dev = {
            dev_id: {
                "rssi_down": [],
                "rssi_up": [],
                "snr_down": [],
                "snr_up": [],
                "psr": [],
                "taxa_teorica": [],
                "taxa_calculada": [],
                "gps_lat": [],
                "gps_lon": [],
                "gps_alt": [],
                "distancia": [],
                "total_pacotes": 0,
                "pacotes_recebidos": 0,
                "pacotes_perdidos": 0,
            }
            for dev_id in lista_end_devices
        }

        for i in range(1, len(linhas)):
            partes = linhas[i].split(",")
            
            # Endereço do End Device está no Byte 10 do Uplink (UL_B10) -> partes[42]
            # Ou no Byte 8 do Downlink (DL_B8) -> partes[10]
            dev_id = int(partes[42]) if len(partes) > 42 else int(partes[10])

            # Se o dispositivo não estiver no dicionário, inclui dinamicamente
            if dev_id not in dados_dev:
                dados_dev[dev_id] = {
                    "rssi_down": [],
                    "rssi_up": [],
                    "snr_down": [],
                    "snr_up": [],
                    "psr": [],
                    "taxa_teorica": [],
                    "taxa_calculada": [],
                    "gps_lat": [],
                    "gps_lon": [],
                    "gps_alt": [],
                    "distancia": [],
                    "total_pacotes": 0,
                    "pacotes_recebidos": 0,
                    "pacotes_perdidos": 0,
                }

            dados_dev[dev_id]["total_pacotes"] += 1

            pacote_recebido = 0
            for j in range(20):
                if int(partes[32 + j]) != 9:
                    pacote_recebido = 1
                    break

            if pacote_recebido == 1:
                dados_dev[dev_id]["pacotes_recebidos"] += 1

                # RSSI / SNR Downlink e Uplink
                UL_B0 = int(partes[32])
                RSSI_DL = (
                    ((UL_B0 - 256) / 2.0) - 74
                    if UL_B0 > 128
                    else (UL_B0 / 2.0) - 74
                )

                UL_B1 = int(partes[33])
                SNR_DL = round(((UL_B1 / 4) - 30), 2)

                UL_B2 = int(partes[34])
                RSSI_UL = (
                    ((UL_B2 - 256) / 2.0) - 74
                    if UL_B2 > 128
                    else (UL_B2 / 2.0) - 74
                )

                UL_B3 = int(partes[35])
                SNR_UL = round(((UL_B3 / 4) - 30), 2)

                # LATITUDE
                blat1, blat2, blat3, blat4 = (
                    int(partes[52]),
                    int(partes[53]),
                    int(partes[54]),
                    int(partes[55]),
                )
                bytes_latitude = bytes([blat1, blat2, blat3, blat4])
                lat_inteira = struct.unpack(">i", bytes_latitude)[0]
                LATITUDE_CALCULADA = round(lat_inteira / 1e6, 6)

                # LONGITUDE
                blon1, blon2, blon3, blon4 = (
                    int(partes[56]),
                    int(partes[57]),
                    int(partes[58]),
                    int(partes[59]),
                )
                bytes_longitude = bytes([blon1, blon2, blon3, blon4])
                lon_inteira = struct.unpack(">i", bytes_longitude)[0]
                LONGITUDE_CALCULADA = round(lon_inteira / 1e6, 6)

                # ALTITUDE
                balt1, balt2 = int(partes[60]), int(partes[61])
                alt_inteira = (balt1 * 256) + balt2
                ALTITUDE_CALCULADA = round(alt_inteira, 0)

                # DISTÂNCIA DO ENLACE
                distancia_enlace = calcula_distancia_enlace(
                    LATITUDE_CALCULADA,
                    LONGITUDE_CALCULADA,
                    ALTITUDE_CALCULADA,
                    GW_LAT,
                    GW_LON,
                    GW_ALT,
                )

                dados_dev[dev_id]["rssi_down"].append(RSSI_DL)
                dados_dev[dev_id]["rssi_up"].append(RSSI_UL)
                dados_dev[dev_id]["snr_down"].append(SNR_DL)
                dados_dev[dev_id]["snr_up"].append(SNR_UL)
                dados_dev[dev_id]["gps_lat"].append(LATITUDE_CALCULADA)
                dados_dev[dev_id]["gps_lon"].append(LONGITUDE_CALCULADA)
                dados_dev[dev_id]["gps_alt"].append(ALTITUDE_CALCULADA)
                dados_dev[dev_id]["distancia"].append(distancia_enlace)

            else:
                dados_dev[dev_id]["pacotes_perdidos"] += 1

            # PSR do dispositivo
            PSR = (
                dados_dev[dev_id]["pacotes_recebidos"]
                / dados_dev[dev_id]["total_pacotes"]
            ) * 100
            dados_dev[dev_id]["psr"].append(PSR)

            # Cálculo de Taxa
            try:
                sf_pacote = int(partes[2])
                bw_pacote = MAPA_BANDWIDTH.get(int(partes[3]), 125)
                cr_pacote = MAPA_CODINGRATE.get(int(partes[4]), 1)
                TAXA_TEORICA, TAXA_CALCULADA = calcula_taxa_canal(
                    sf_pacote, bw_pacote, cr_pacote, PSR
                )
            except (ValueError, ZeroDivisionError):
                TAXA_TEORICA, TAXA_CALCULADA = None, None

            dados_dev[dev_id]["taxa_teorica"].append(TAXA_TEORICA)
            dados_dev[dev_id]["taxa_calculada"].append(TAXA_CALCULADA)

        # Gravação dos arquivos .tmp específicos para cada End Device
        for dev_id, info in dados_dev.items():
            if info["total_pacotes"] == 0:
                continue

            arquivo_rssi = os.path.join(pasta_dados_processados, f"{dev_id}_rssi.tmp")
            arquivo_psr = os.path.join(pasta_dados_processados, f"{dev_id}_psr.tmp")
            arquivo_gps = os.path.join(pasta_dados_processados, f"{dev_id}_gps.tmp")
            arquivo_stats = os.path.join(pasta_dados_processados, f"{dev_id}_stats.tmp")
            arquivo_taxa = os.path.join(pasta_dados_processados, f"{dev_id}_taxa_dados.tmp")

            rssi_down_min = min(info["rssi_down"]) if info["rssi_down"] else None
            rssi_down_max = max(info["rssi_down"]) if info["rssi_down"] else None
            rssi_up_min = min(info["rssi_up"]) if info["rssi_up"] else None
            rssi_up_max = max(info["rssi_up"]) if info["rssi_up"] else None
            snr_down_min = min(info["snr_down"]) if info["snr_down"] else None
            snr_down_max = max(info["snr_down"]) if info["snr_down"] else None
            snr_up_min = min(info["snr_up"]) if info["snr_up"] else None
            snr_up_max = max(info["snr_up"]) if info["snr_up"] else None

            # Grava RSSI / SNR
            with open(arquivo_rssi, "w") as f_rssi:
                for idx in range(len(info["rssi_down"])):
                    print(
                        info["rssi_down"][idx],
                        info["rssi_up"][idx],
                        info["snr_down"][idx],
                        info["snr_up"][idx],
                        file=f_rssi,
                    )

            # Grava PSR
            with open(arquivo_psr, "w") as f_psr:
                for val in info["psr"]:
                    print(val, file=f_psr)

            # Grava Taxa de Dados
            with open(arquivo_taxa, "w") as f_taxa:
                for idx in range(len(info["taxa_teorica"])):
                    print(
                        info["taxa_teorica"][idx],
                        info["taxa_calculada"][idx],
                        file=f_taxa,
                    )

            # Grava GPS / Distância
            with open(arquivo_gps, "w") as f_gps:
                for idx in range(len(info["gps_lat"])):
                    print(
                        info["gps_lat"][idx],
                        info["gps_lon"][idx],
                        info["gps_alt"][idx],
                        info["distancia"][idx],
                        file=f_gps,
                    )

            # Grava Estatísticas
            with open(arquivo_stats, "w") as f_stats:
                print(
                    rssi_down_min,
                    rssi_down_max,
                    rssi_up_min,
                    rssi_up_max,
                    snr_down_min,
                    snr_down_max,
                    snr_up_min,
                    snr_up_max,
                    info["pacotes_perdidos"],
                    file=f_stats,
                )

            print(
                f"[N5] Sensor ID = {dev_id} | Pacotes = {info['total_pacotes']} "
                f"| Recebidos = {info['pacotes_recebidos']} | Perdidos = {info['pacotes_perdidos']} "
                f"| PSR = {info['psr'][-1] if info['psr'] else 0:.2f}%"
            )

        time.sleep(1)

    except KeyboardInterrupt:
        print("\n[Ctrl + C] Interrompido pelo usuário.")
        break
    
#===========================================================
#Vs-2
'''
# FEE247 - Desenvolvimento de Soluções IoT com LoRa e LoRaWAN
# ======= Nível 5 - Gerência ============
# Extrai RSSI dos dados brutos e calcula a PSR

# FEE247 - Desenvolvimento de Soluções IoT com LoRa e LoRaWAN
# ======= Nível 5 - Gerência ============
# Extrai RSSI dos dados brutos e calcula a PSR
import math
import os
import re
import struct
import time

# Diretores de Parâmetros e Dados Processados (Nível 4)
dir_nivel4 = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../3_N4_Armazenamento/Parametros/",
)
arquivo_gw_gps = os.path.join(dir_nivel4, "gateway_gps.txt")
arquivo_propagacao = os.path.join(dir_nivel4, "parametros_propagacao.txt")

# Caminho da pasta de destino dos dados processados
pasta_dados_processados = os.path.join(
    "..", "3_N4_Armazenamento", "Dados_Processados"
)

# Garante que a pasta existe antes de manipular os arquivos
os.makedirs(pasta_dados_processados, exist_ok=True)

# Define o caminho completo dos arquivos .tmp
arquivo_rssi = os.path.join(pasta_dados_processados, "rssi.tmp")
arquivo_psr = os.path.join(pasta_dados_processados, "psr.tmp")
arquivo_gps = os.path.join(pasta_dados_processados, "gps.tmp")
arquivo_stats = os.path.join(pasta_dados_processados, "stats.tmp")
arquivo_taxa = os.path.join(pasta_dados_processados, "taxa_dados.tmp")
arquivo_propagacao = os.path.join(pasta_dados_processados, "propagacao.tmp")

# MAPAS DE CONFIGURAÇÃO DE RÁDIO
MAPA_BANDWIDTH = {1: 125, 2: 250, 3: 500}
MAPA_CODINGRATE = {5: 1, 6: 2, 7: 3, 8: 4}

TAMANHO_PACOTE = 30
pacote_perdido = 0


def ler_gateway_gps():
    """Lê as coordenadas do Gateway a partir do arquivo gateway_gps.txt.

    Retorna valores padrão caso o arquivo não exista ou esteja corrompido.
    """
    gw_lat, gw_lon, gw_alt = -23.005380, -46.835336, 770.0

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
            print(f"Erro ao ler arquivo de parâmetros do Gateway: {e}")

    return gw_lat, gw_lon, gw_alt


def calcula_toa_taxa_canal(
    spreading_factor,
    bandwidth_khz,
    coding_rate,
    tamanho_pacote=TAMANHO_PACOTE,
    n_preambulo=8,
    header_impl=False,
    crc_on=True,
    low_dr_opt=None,
):
    bandwidth_hz = bandwidth_khz * 1000
    tempo_simbolo = (2**spreading_factor) / bandwidth_hz

    tempo_preambulo = (n_preambulo + 4.25) * tempo_simbolo

    if low_dr_opt is None:
        low_dr_opt = 1 if tempo_simbolo > 0.016 else 0

    valor_cr = coding_rate

    ih = 1 if header_impl else 0
    crc = 1 if crc_on else 0
    de = 1 if low_dr_opt else 0

    n_pacote = (
        8 * tamanho_pacote - 4 * spreading_factor + 28 + 16 * crc - 20 * ih
    ) / (4 * (spreading_factor - 2 * de))
    n_payload_simbolo = 8 + max(math.ceil(n_pacote) * (valor_cr + 4), 0)

    tempo_pacote_toa = n_payload_simbolo * tempo_simbolo
    toa_s = tempo_preambulo + tempo_pacote_toa
    toa_ms = toa_s * 1000

    cr = 4 / (4 + valor_cr)
    taxa_teorica = (
        spreading_factor * (bandwidth_hz / (2**spreading_factor)) * cr
    )

    return toa_ms, round(taxa_teorica, 3)


def calcula_taxa_canal(
    spreading_factor, bandwidth_khz, coding_rate, psr_percentual
):
    _, taxa_teorica = calcula_toa_taxa_canal(
        spreading_factor, bandwidth_khz, coding_rate
    )
    taxa_calculada = round((taxa_teorica * psr_percentual) / 100, 3)
    return taxa_teorica, taxa_calculada


def calcula_distancia_enlace(lat1, lon1, alt1, lat2, lon2, alt2):
    """Calcula a distância 3D em metros entre duas coordenadas geográficas (Haversine + diferença de altitude)."""
    if None in (lat1, lon1, alt1, lat2, lon2, alt2):
        return None

    R = 6371000.0  # Raio médio da Terra em metros
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    dist_2d = R * c

    dalt = alt2 - alt1
    dist_3d = math.sqrt(dist_2d**2 + dalt**2)

    return round(dist_3d, 2)


# Pasta de dados brutos
PASTA_ARMAZENAMENTO = os.path.join("..", "3_N4_Armazenamento")
pasta_dados_brutos = os.path.join(PASTA_ARMAZENAMENTO, "Dados_Brutos")

while True:
    try:
        # Lê dinamicamente os dados atualizados do Gateway
        GW_LAT, GW_LON, GW_ALT = ler_gateway_gps()

        arquivo_entrada = ""
        if os.path.exists(pasta_dados_brutos):
            arquivos = os.listdir(pasta_dados_brutos)
            arquivos.sort()
            for nome in arquivos:
                if nome.endswith(".txt"):
                    arquivo_entrada = os.path.join(pasta_dados_brutos, nome)

        if not arquivo_entrada:
            time.sleep(1)
            continue

        try:
            arquivo = open(arquivo_entrada, "r")
            linhas = arquivo.readlines()
            arquivo.close()
        except (FileNotFoundError, PermissionError):
            time.sleep(1)
            continue

        rssi_down = []
        rssi_up = []
        snr_down = []
        snr_up = []
        psr = []
        taxa_teorica_lista = []
        taxa_calculada_lista = []
        gps_latitude = []
        gps_longitude = []
        gps_altitude = []
        distancia_enlace_lista = []

        total_pacotes = 0
        pacotes_recebidos = 0
        pacote_perdido = 0

        RSSI_DL = None
        RSSI_UL = None
        SNR_DL = None
        SNR_UL = None
        PSR = 0
        TAXA_TEORICA = None
        TAXA_CALCULADA = None
        LATITUDE_CALCULADA = None
        LONGITUDE_CALCULADA = None
        ALTITUDE_CALCULADA = None
        distancia_enlace = None

        for i in range(1, len(linhas)):
            partes = linhas[i].split(",")
            total_pacotes = total_pacotes + 1

            pacote_recebido = 0
            for j in range(20):
                if int(partes[32 + j]) != 9:
                    pacote_recebido = 1

            if pacote_recebido == 1:
                pacotes_recebidos = pacotes_recebidos + 1

                # RSSI / SNR Downlink e Uplink
                UL_B0 = int(partes[32])
                RSSI_DL = (
                    ((UL_B0 - 256) / 2.0) - 74
                    if UL_B0 > 128
                    else (UL_B0 / 2.0) - 74
                )

                UL_B1 = int(partes[33])
                SNR_DL = round(((UL_B1 / 4) - 30), 2)

                UL_B2 = int(partes[34])
                RSSI_UL = (
                    ((UL_B2 - 256) / 2.0) - 74
                    if UL_B2 > 128
                    else (UL_B2 / 2.0) - 74
                )

                UL_B3 = int(partes[35])
                SNR_UL = round(((UL_B3 / 4) - 30), 2)

                # LATITUDE
                blat1, blat2, blat3, blat4 = (
                    int(partes[52]),
                    int(partes[53]),
                    int(partes[54]),
                    int(partes[55]),
                )
                bytes_latitude = bytes([blat1, blat2, blat3, blat4])
                lat_inteira = struct.unpack(">i", bytes_latitude)[0]
                LATITUDE_CALCULADA = round(lat_inteira / 1e6, 6)

                # LONGITUDE
                blon1, blon2, blon3, blon4 = (
                    int(partes[56]),
                    int(partes[57]),
                    int(partes[58]),
                    int(partes[59]),
                )
                bytes_longitude = bytes([blon1, blon2, blon3, blon4])
                lon_inteira = struct.unpack(">i", bytes_longitude)[0]
                LONGITUDE_CALCULADA = round(lon_inteira / 1e6, 6)

                # ALTITUDE
                balt1, balt2 = int(partes[60]), int(partes[61])
                alt_inteira = (balt1 * 256) + balt2
                ALTITUDE_CALCULADA = round(alt_inteira, 0)

                # CÁLCULO DA DISTÂNCIA DO ENLACE (COM O GW_LAT, GW_LON, GW_ALT LIDOS DO ARQUIVO)
                distancia_enlace = calcula_distancia_enlace(
                    LATITUDE_CALCULADA,
                    LONGITUDE_CALCULADA,
                    ALTITUDE_CALCULADA,
                    GW_LAT,
                    GW_LON,
                    GW_ALT,
                )

                rssi_down.append(RSSI_DL)
                rssi_up.append(RSSI_UL)
                snr_down.append(SNR_DL)
                snr_up.append(SNR_UL)
                gps_latitude.append(LATITUDE_CALCULADA)
                gps_longitude.append(LONGITUDE_CALCULADA)
                gps_altitude.append(ALTITUDE_CALCULADA)
                distancia_enlace_lista.append(distancia_enlace)

            else:
                pacote_perdido = pacote_perdido + 1

            PSR = (pacotes_recebidos / total_pacotes) * 100
            psr.append(PSR)

            try:
                sf_pacote = int(partes[2])
                bw_pacote = MAPA_BANDWIDTH.get(int(partes[3]), 125)
                cr_pacote = MAPA_CODINGRATE.get(int(partes[4]), 1)
                TAXA_TEORICA, TAXA_CALCULADA = calcula_taxa_canal(
                    sf_pacote, bw_pacote, cr_pacote, PSR
                )
            except (ValueError, ZeroDivisionError):
                TAXA_TEORICA, TAXA_CALCULADA = None, None

            taxa_teorica_lista.append(TAXA_TEORICA)
            taxa_calculada_lista.append(TAXA_CALCULADA)

        rssi_down_min = min(rssi_down) if rssi_down else None
        rssi_down_max = max(rssi_down) if rssi_down else None
        rssi_up_min = min(rssi_up) if rssi_up else None
        rssi_up_max = max(rssi_up) if rssi_up else None
        snr_down_min = min(snr_down) if snr_down else None
        snr_down_max = max(snr_down) if snr_down else None
        snr_up_min = min(snr_up) if snr_up else None
        snr_up_max = max(snr_up) if snr_up else None

        f_rssi = open(arquivo_rssi, "w")
        for i in range(len(rssi_down)):
            print(
                rssi_down[i], rssi_up[i], snr_down[i], snr_up[i], file=f_rssi
            )
        f_rssi.close()

        f_psr = open(arquivo_psr, "w")
        for i in range(len(psr)):
            print(psr[i], file=f_psr)
        f_psr.close()

        f_taxa = open(arquivo_taxa, "w")
        for i in range(len(taxa_teorica_lista)):
            print(taxa_teorica_lista[i], taxa_calculada_lista[i], file=f_taxa)
        f_taxa.close()

        f_gps = open(arquivo_gps, "w")
        for i in range(len(gps_latitude)):
            print(
                gps_latitude[i],
                gps_longitude[i],
                gps_altitude[i],
                distancia_enlace_lista[i],
                file=f_gps,
            )
        f_gps.close()

        f_stats = open(arquivo_stats, "w")
        print(
            rssi_down_min,
            rssi_down_max,
            rssi_up_min,
            rssi_up_max,
            snr_down_min,
            snr_down_max,
            snr_up_min,
            snr_up_max,
            pacote_perdido,
            file=f_stats,
        )
        f_stats.close()

        print(
            "Arquivo = ",
            arquivo_entrada,
            " | Pacotes = ",
            total_pacotes,
            " | Recebidos = ",
            pacotes_recebidos,
            " | PSR = ",
            PSR,
            "| RSSI Downlink = ",
            RSSI_DL,
            "| RSSI Uplink = ",
            RSSI_UL,
            "| SNR Downlink = ",
            SNR_DL,
            "| SNR Uplink = ",
            SNR_UL,
            "| RSSI DL min/max = ",
            rssi_down_min,
            rssi_down_max,
            "| RSSI UL min/max = ",
            rssi_up_min,
            rssi_up_max,
            "| SNR DL min/max = ",
            snr_down_min,
            snr_down_max,
            "| SNR UL min/max = ",
            snr_up_min,
            snr_up_max,
            "| Taxa Canal Teórica (bps) = ",
            TAXA_TEORICA,
            "| Taxa Canal Calculada (bps) = ",
            TAXA_CALCULADA,
            "| LATITUDE = ",
            LATITUDE_CALCULADA,
            "| LONGITUDE = ",
            LONGITUDE_CALCULADA,
            "| ALTITUDE = ",
            ALTITUDE_CALCULADA,
            "| DISTÂNCIA ENLACE (m) = ",
            distancia_enlace,
            "| Pacotes Perdidos = ",
            pacote_perdido,
        )
        time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Ctrl + C] Interrompido pelo usuário.")
        
'''
#===========================================================
#Vs-1
'''
import math
import os
import struct
import time

# Coordenadas fixas do Gateway GPS (Latitude, Longitude, Altitude em metros)
GW_LAT = -23.005380
GW_LON = -46.835336
GW_ALT = 770.0

# Arquivos utilizados pelo nível 5 de gerência

# Caminho da pasta de destino dos dados processados
pasta_dados_processados = os.path.join(
    "..", "3_N4_Armazenamento", "Dados_Processados"
)

# Garante que a pasta existe antes de manipular os arquivos
os.makedirs(pasta_dados_processados, exist_ok=True)

# Define o caminho completo dos arquivos .tmp
arquivo_rssi = os.path.join(pasta_dados_processados, "rssi.tmp")
arquivo_psr = os.path.join(pasta_dados_processados, "psr.tmp")
arquivo_gps = os.path.join(pasta_dados_processados, "gps.tmp")
# Arquivo com os valores de Máximo e Mínimo de RSSI e SNR (DL/UL) da rodada
arquivo_stats = os.path.join(pasta_dados_processados, "stats.tmp")
# Arquivo com a Taxa de Canal Teórica e a Taxa de Canal Calculada (real)
arquivo_taxa = os.path.join(pasta_dados_processados, "taxa_dados.tmp")

# MAPAS DE CONFIGURAÇÃO DE RÁDIO
MAPA_BANDWIDTH = {1: 125, 2: 250, 3: 500}
MAPA_CODINGRATE = {5: 1, 6: 2, 7: 3, 8: 4}

TAMANHO_PACOTE = 30
pacote_perdido = 0


def calcula_toa_taxa_canal(
    spreading_factor,
    bandwidth_khz,
    coding_rate,
    tamanho_pacote=TAMANHO_PACOTE,
    n_preambulo=8,
    header_impl=False,
    crc_on=True,
    low_dr_opt=None,
):
    bandwidth_hz = bandwidth_khz * 1000
    tempo_simbolo = (2**spreading_factor) / bandwidth_hz

    tempo_preambulo = (n_preambulo + 4.25) * tempo_simbolo

    if low_dr_opt is None:
        low_dr_opt = 1 if tempo_simbolo > 0.016 else 0

    valor_cr = coding_rate

    ih = 1 if header_impl else 0
    crc = 1 if crc_on else 0
    de = 1 if low_dr_opt else 0

    n_pacote = (
        8 * tamanho_pacote - 4 * spreading_factor + 28 + 16 * crc - 20 * ih
    ) / (4 * (spreading_factor - 2 * de))
    n_payload_simbolo = 8 + max(math.ceil(n_pacote) * (valor_cr + 4), 0)

    tempo_pacote_toa = n_payload_simbolo * tempo_simbolo
    toa_s = tempo_preambulo + tempo_pacote_toa
    toa_ms = toa_s * 1000

    cr = 4 / (4 + valor_cr)
    taxa_teorica = (
        spreading_factor * (bandwidth_hz / (2**spreading_factor)) * cr
    )

    return toa_ms, round(taxa_teorica, 3)


def calcula_taxa_canal(
    spreading_factor, bandwidth_khz, coding_rate, psr_percentual
):
    _, taxa_teorica = calcula_toa_taxa_canal(
        spreading_factor, bandwidth_khz, coding_rate
    )
    taxa_calculada = round((taxa_teorica * psr_percentual) / 100, 3)
    return taxa_teorica, taxa_calculada


def calcula_distancia_enlace(lat1, lon1, alt1, lat2, lon2, alt2):
    """Calcula a distância 3D em metros entre duas coordenadas geográficas (Haversine + diferença de altitude)."""
    if None in (lat1, lon1, alt1, lat2, lon2, alt2):
        return None

    R = 6371000.0  # Raio médio da Terra em metros
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    dist_2d = R * c

    dalt = alt2 - alt1
    dist_3d = math.sqrt(dist_2d**2 + dalt**2)

    return round(dist_3d, 2)


# Define a pasta onde estão os dados brutos
PASTA_ARMAZENAMENTO = os.path.join("..", "3_N4_Armazenamento")
pasta_dados_brutos = os.path.join(PASTA_ARMAZENAMENTO, "Dados_Brutos")

while True:
    try:
        arquivo_entrada = ""
        if os.path.exists(pasta_dados_brutos):
            arquivos = os.listdir(pasta_dados_brutos)
            arquivos.sort()
            for nome in arquivos:
                if nome.endswith(".txt"):
                    arquivo_entrada = os.path.join(pasta_dados_brutos, nome)

        if not arquivo_entrada:
            time.sleep(1)
            continue

        try:
            arquivo = open(arquivo_entrada, "r")
            linhas = arquivo.readlines()
            arquivo.close()
        except (FileNotFoundError, PermissionError):
            time.sleep(1)
            continue

        rssi_down = []
        rssi_up = []
        snr_down = []
        snr_up = []
        psr = []
        taxa_teorica_lista = []
        taxa_calculada_lista = []
        gps_latitude = []
        gps_longitude = []
        gps_altitude = []
        distancia_enlace_lista = []

        total_pacotes = 0
        pacotes_recebidos = 0
        pacote_perdido = 0

        RSSI_DL = None
        RSSI_UL = None
        SNR_DL = None
        SNR_UL = None
        PSR = 0
        TAXA_TEORICA = None
        TAXA_CALCULADA = None
        LATITUDE_CALCULADA = None
        LONGITUDE_CALCULADA = None
        ALTITUDE_CALCULADA = None
        distancia_enlace = None

        for i in range(1, len(linhas)):
            partes = linhas[i].split(",")
            total_pacotes = total_pacotes + 1

            pacote_recebido = 0
            for j in range(20):
                if int(partes[32 + j]) != 9:
                    pacote_recebido = 1

            if pacote_recebido == 1:
                pacotes_recebidos = pacotes_recebidos + 1

                # RSSI / SNR Downlink e Uplink
                UL_B0 = int(partes[32])
                RSSI_DL = ((UL_B0 - 256) / 2.0) - 74 if UL_B0 > 128 else (UL_B0 / 2.0) - 74

                UL_B1 = int(partes[33])
                SNR_DL = round(((UL_B1 / 4) - 30), 2)

                UL_B2 = int(partes[34])
                RSSI_UL = ((UL_B2 - 256) / 2.0) - 74 if UL_B2 > 128 else (UL_B2 / 2.0) - 74

                UL_B3 = int(partes[35])
                SNR_UL = round(((UL_B3 / 4) - 30), 2)

                # LATITUDE
                blat1, blat2, blat3, blat4 = (
                    int(partes[52]),
                    int(partes[53]),
                    int(partes[54]),
                    int(partes[55]),
                )
                bytes_latitude = bytes([blat1, blat2, blat3, blat4])
                lat_inteira = struct.unpack(">i", bytes_latitude)[0]
                LATITUDE_CALCULADA = round(lat_inteira / 1e6, 6)

                # LONGITUDE
                blon1, blon2, blon3, blon4 = (
                    int(partes[56]),
                    int(partes[57]),
                    int(partes[58]),
                    int(partes[59]),
                )
                bytes_longitude = bytes([blon1, blon2, blon3, blon4])
                lon_inteira = struct.unpack(">i", bytes_longitude)[0]
                LONGITUDE_CALCULADA = round(lon_inteira / 1e6, 6)

                # ALTITUDE
                balt1, balt2 = int(partes[60]), int(partes[61])
                alt_inteira = (balt1 * 256) + balt2
                ALTITUDE_CALCULADA = round(alt_inteira, 0)

                # CÁLCULO DA DISTÂNCIA DO ENLACE (EM METROS)
                distancia_enlace = calcula_distancia_enlace(
                    LATITUDE_CALCULADA,
                    LONGITUDE_CALCULADA,
                    ALTITUDE_CALCULADA,
                    GW_LAT,
                    GW_LON,
                    GW_ALT,
                )

                rssi_down.append(RSSI_DL)
                rssi_up.append(RSSI_UL)
                snr_down.append(SNR_DL)
                snr_up.append(SNR_UL)
                gps_latitude.append(LATITUDE_CALCULADA)
                gps_longitude.append(LONGITUDE_CALCULADA)
                gps_altitude.append(ALTITUDE_CALCULADA)
                distancia_enlace_lista.append(distancia_enlace)

            else:
                pacote_perdido = pacote_perdido + 1

            PSR = (pacotes_recebidos / total_pacotes) * 100
            psr.append(PSR)

            try:
                sf_pacote = int(partes[2])
                bw_pacote = MAPA_BANDWIDTH.get(int(partes[3]), 125)
                cr_pacote = MAPA_CODINGRATE.get(int(partes[4]), 1)
                TAXA_TEORICA, TAXA_CALCULADA = calcula_taxa_canal(
                    sf_pacote, bw_pacote, cr_pacote, PSR
                )
            except (ValueError, ZeroDivisionError):
                TAXA_TEORICA, TAXA_CALCULADA = None, None

            taxa_teorica_lista.append(TAXA_TEORICA)
            taxa_calculada_lista.append(TAXA_CALCULADA)

        rssi_down_min = min(rssi_down) if rssi_down else None
        rssi_down_max = max(rssi_down) if rssi_down else None
        rssi_up_min = min(rssi_up) if rssi_up else None
        rssi_up_max = max(rssi_up) if rssi_up else None
        snr_down_min = min(snr_down) if snr_down else None
        snr_down_max = max(snr_down) if snr_down else None
        snr_up_min = min(snr_up) if snr_up else None
        snr_up_max = max(snr_up) if snr_up else None

        f_rssi = open(arquivo_rssi, "w")
        for i in range(len(rssi_down)):
            print(
                rssi_down[i], rssi_up[i], snr_down[i], snr_up[i], file=f_rssi
            )
        f_rssi.close()

        f_psr = open(arquivo_psr, "w")
        for i in range(len(psr)):
            print(psr[i], file=f_psr)
        f_psr.close()

        f_taxa = open(arquivo_taxa, "w")
        for i in range(len(taxa_teorica_lista)):
            print(taxa_teorica_lista[i], taxa_calculada_lista[i], file=f_taxa)
        f_taxa.close()

        f_gps = open(arquivo_gps, "w")
        for i in range(len(gps_latitude)):
            print(
                gps_latitude[i],
                gps_longitude[i],
                gps_altitude[i],
                distancia_enlace_lista[i],
                file=f_gps,
            )
        f_gps.close()

        f_stats = open(arquivo_stats, "w")
        print(
            rssi_down_min,
            rssi_down_max,
            rssi_up_min,
            rssi_up_max,
            snr_down_min,
            snr_down_max,
            snr_up_min,
            snr_up_max,
            pacote_perdido,
            file=f_stats,
        )
        f_stats.close()

        print(
            "Arquivo = ",
            arquivo_entrada,
            " | Pacotes = ",
            total_pacotes,
            " | Recebidos = ",
            pacotes_recebidos,
            " | PSR = ",
            PSR,
            "| RSSI Downlink = ",
            RSSI_DL,
            "| RSSI Uplink = ",
            RSSI_UL,
            "| SNR Downlink = ",
            SNR_DL,
            "| SNR Uplink = ",
            SNR_UL,
            "| RSSI DL min/max = ",
            rssi_down_min,
            rssi_down_max,
            "| RSSI UL min/max = ",
            rssi_up_min,
            rssi_up_max,
            "| SNR DL min/max = ",
            snr_down_min,
            snr_down_max,
            "| SNR UL min/max = ",
            snr_up_min,
            snr_up_max,
            "| Taxa Canal Teórica (bps) = ",
            TAXA_TEORICA,
            "| Taxa Canal Calculada (bps) = ",
            TAXA_CALCULADA,
            "| LATITUDE = ",
            LATITUDE_CALCULADA,
            "| LONGITUDE = ",
            LONGITUDE_CALCULADA,
            "| ALTITUDE = ",
            ALTITUDE_CALCULADA,
            "| DISTÂNCIA ENLACE (m) = ",
            distancia_enlace,
            "| Pacotes Perdidos = ",
            pacote_perdido,
        )
        time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Ctrl + C] Interrompido pelo usuário.")
'''
