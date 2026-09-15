# FEE247 - Desenvolvimento de Soluções IoT com LoRa e LoRaWAN
#======= Nível 5 - Gerência ============
# Extrai RSSI dos dados brutos e calcula a PSR
import time
import os

# Arquivos utilizados pelo nível 5 de gerência

# Caminho da pasta de destino dos dados processados
pasta_dados_processados = os.path.join("..", "3_N4_Armazenamento", "Dados_Processados")

# Garante que a pasta existe antes de manipular os arquivos
os.makedirs(pasta_dados_processados, exist_ok=True)

# Define o caminho completo dos arquivos .tmp
arquivo_rssi = os.path.join(pasta_dados_processados, "rssi.tmp")
arquivo_psr = os.path.join(pasta_dados_processados, "psr.tmp")
# Arquivo com os valores de Máximo e Mínimo de RSSI e SNR (DL/UL) da rodada
arquivo_stats = os.path.join(pasta_dados_processados, "stats.tmp")

# Define a pasta onde estão os dados brutos
PASTA_ARMAZENAMENTO = os.path.join("..", "3_N4_Armazenamento")
pasta_dados_brutos = os.path.join(PASTA_ARMAZENAMENTO, "Dados_Brutos")

while True:

    # Procura o último arquivo de dados brutos gravado no nível 4
    arquivo_entrada = ""
    if os.path.exists(pasta_dados_brutos):
        arquivos = os.listdir(pasta_dados_brutos)
        arquivos.sort()
        for nome in arquivos:
            if nome.endswith(".txt"):
                arquivo_entrada = os.path.join(pasta_dados_brutos, nome)


    # Abre o arquivo de dados brutos
    arquivo = open(arquivo_entrada,"r")
    linhas = arquivo.readlines()
    arquivo.close()

    # Listas que guardam os valores calculados
    rssi_down = []
    rssi_up = []
    snr_down = []
    snr_up = []
    psr = []

    # Contadores usados para calcular a PSR
    total_pacotes = 0
    pacotes_recebidos = 0

    # Começa em 1 para pular o cabeçalho do arquivo
    for i in range(1,len(linhas)):
        partes = linhas[i].split(",")
        total_pacotes = total_pacotes + 1

        # Se todos os bytes do UL forem diferente de 9, considera pacote recebido
        pacote_recebido = 0
        for j in range(20):
            if int(partes[22+j]) != 9:
                pacote_recebido = 1

        if pacote_recebido == 1:
            pacotes_recebidos = pacotes_recebidos + 1

            # RSSI de downlink no byte UL_B0 (Posição 38)
            UL_B0 = int(partes[22]) #22 aaf
            if UL_B0 > 128:
                RSSI_DL = ((UL_B0-256)/2.0)-74
            else:
                RSSI_DL = (UL_B0/2.0)-74

            # SNR de downlink no byte UL_B1 (Posição 39)
            UL_B1 = int(partes[23])
            SNR_DL = round(((UL_B1 / 4) - 30),2)

            # RSSI de uplink no byte UL_B2 (Posição 40)
            UL_B2 = int(partes[24])
            if UL_B2 > 128:
                RSSI_UL = ((UL_B2-256)/2.0)-74
            else:
                RSSI_UL = (UL_B2/2.0)-74

            # SNR de downlink no byte UL_B3 (Posição 41)
            UL_B3 = int(partes[25])
            SNR_UL = round(((UL_B3 / 4) - 30),2)

            rssi_down.append(RSSI_DL)
            rssi_up.append(RSSI_UL)
            snr_down.append(SNR_DL)
            snr_up.append(SNR_UL)


        # Calcula a PSR acumulada até este pacote
        PSR = (pacotes_recebidos/total_pacotes)*100
        psr.append(PSR)

    # Calcula os valores de Máximo e Mínimo de RSSI e SNR (DL/UL)
    # observados na rodada até o momento. Usa None quando ainda não há
    # nenhum pacote recebido, para que o Nível 6 possa exibir "--".
    if rssi_down:
        rssi_down_min = min(rssi_down)
        rssi_down_max = max(rssi_down)
    else:
        rssi_down_min = None
        rssi_down_max = None

    if rssi_up:
        rssi_up_min = min(rssi_up)
        rssi_up_max = max(rssi_up)
    else:
        rssi_up_min = None
        rssi_up_max = None

    if snr_down:
        snr_down_min = min(snr_down)
        snr_down_max = max(snr_down)
    else:
        snr_down_min = None
        snr_down_max = None

    if snr_up:
        snr_up_min = min(snr_up)
        snr_up_max = max(snr_up)
    else:
        snr_up_min = None
        snr_up_max = None

    # Grava as RSSIs em arquivo temporário
    f_rssi = open(arquivo_rssi,"w")
    for i in range(len(rssi_down)):
        print(rssi_down[i],rssi_up[i],snr_down[i],snr_up[i],file=f_rssi)
    f_rssi.close()

    # Grava a PSR em arquivo temporário
    f_psr = open(arquivo_psr,"w")
    for i in range(len(psr)):
        print(psr[i],file=f_psr)
    f_psr.close()

    # Grava os Máximos e Mínimos em arquivo temporário. Cada campo é
    # gravado como "None" quando ainda não há dado disponível (nenhum
    # pacote recebido até o momento), e o Nível 6 trata essa string ao
    # ler o arquivo.
    f_stats = open(arquivo_stats,"w")
    print(rssi_down_min, rssi_down_max, rssi_up_min, rssi_up_max,
          snr_down_min, snr_down_max, snr_up_min, snr_up_max, file=f_stats)
    f_stats.close()

    print("Arquivo = ",arquivo_entrada," | Pacotes = ",total_pacotes," | Recebidos = ",pacotes_recebidos," | PSR = ",PSR,
          "| RSSI Downlink = ", RSSI_DL, "| RSSI Uplink = ", RSSI_UL, "| SNR Downlink = ", SNR_DL, "| SNR Uplink = ", SNR_UL,
          "| RSSI DL min/max = ", rssi_down_min, rssi_down_max, "| RSSI UL min/max = ", rssi_up_min, rssi_up_max,
          "| SNR DL min/max = ", snr_down_min, snr_down_max, "| SNR UL min/max = ", snr_up_min, snr_up_max)
    time.sleep(1)
