# FEE247 - Desenvolvimento de Soluções IoT com LoRa e LoRaWAN
#======= Nível 5 - Gerência ============
# Extrai RSSI dos dados brutos e calcula a PSR
import time
import os
import math

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
# Arquivo com a Taxa de Canal Teórica e a Taxa de Canal Calculada (real)
arquivo_taxa = os.path.join(pasta_dados_processados, "taxa_dados.tmp")

# =============================================================================
# Cálculo da Taxa de Canal LoRa (bps)
# =============================================================================
# No Pacote DL (bytes de configuração de rádio):
#   Byte 0 -> Spreading Factor (SF)
#   Byte 1 -> Bandwidth        [0 = 125 kHz, 1 = 250 kHz, 3 = 500 kHz]
#   Byte 3 -> Coding Rate      [5..8 => 4/5, 4/6, 4/7, 4/8]
#
# Mesma lógica de cálculo utilizada no Nível 2/3 (calculaTaxaCanal), agora
# aplicada no Nível 5 a partir dos bytes de configuração lidos diretamente
# do Pacote DL de cada linha do arquivo de dados brutos.
MAPA_BANDWIDTH = {1: 125, 2: 250, 3: 500}
MAPA_CODINGRATE = {5: 1, 6: 2, 7: 3, 8: 4}

# Tamanho do payload (em bytes) considerado no cálculo do ToA. Ajuste este
# valor se o tamanho real do pacote LoRa (PHY payload) for diferente — aqui
# foi assumido 20 bytes, mesmo tamanho dos blocos DL/UL lidos do arquivo de
# dados brutos. Se o framework tiver esse valor em outra variável/arquivo,
# troque esta constante pela referência correta.
TAMANHO_PACOTE = 20
pacote_perdido = 0

def calcula_toa_taxa_canal(spreading_factor, bandwidth_khz, coding_rate, tamanho_pacote=TAMANHO_PACOTE,
                            n_preambulo=8, header_impl=False, crc_on=True, low_dr_opt=None):
    """Calcula o Time on Air (ToA, em ms) e a Taxa de Canal Teórica (bps)
    real de um pacote LoRa, a partir de SF, BW e CR.

    Diferente da fórmula nominal anterior (SF*(BW/2^SF)*(4/(4+CR))), que é
    apenas uma taxa de símbolo aproximada e praticamente não diferenciava o
    Coding Rate no resultado final, este cálculo usa o modelo de ToA do
    padrão LoRa (mesmo usado no cálculo de tempo entre medidas), que pondera
    corretamente o overhead introduzido por cada CR sobre o payload.
    """
    bandwidth_hz = bandwidth_khz * 1000
    tempo_simbolo = (2 ** spreading_factor) / bandwidth_hz

    tempo_preambulo = (n_preambulo + 4.25) * tempo_simbolo

    # Low Data Rate Optimization automático quando o símbolo > 16 ms
    if low_dr_opt is None:
        low_dr_opt = 1 if tempo_simbolo > 0.016 else 0

    # coding_rate já chega no formato 1..4 (equivalente a CR 4/5 .. 4/8),
    # de acordo com o MAPA_CODINGRATE

    valor_cr = coding_rate
    
    ih = 1 if header_impl else 0
    crc = 1 if crc_on else 0
    de = 1 if low_dr_opt else 0

    n_pacote = (8 * tamanho_pacote - 4 * spreading_factor + 28 + 16 * crc - 20 * ih) / (4 * (spreading_factor - 2 * de))
    n_payload_simbolo = 8 + max(math.ceil(n_pacote) * (valor_cr + 4), 0)

    tempo_pacote_toa = n_payload_simbolo * tempo_simbolo
    toa_s = tempo_preambulo + tempo_pacote_toa
    toa_ms = toa_s * 1000

    # Eficiência do Coding Rate: 4 / (4 + CR)
    cr = 4 / (4 + valor_cr)
        
    # Taxa de bits teórica
    taxa_teorica = spreading_factor * (bandwidth_hz / (2**spreading_factor)) * cr   

    return toa_ms, round(taxa_teorica, 3)


def calcula_taxa_canal(spreading_factor, bandwidth_khz, coding_rate, psr_percentual):
    """Calcula a Taxa de Canal Teórica (bps) real a partir de SF/BW/CR
    (via ToA) e a Taxa de Canal Calculada (real), que é a taxa teórica
    ponderada pela PSR (Packet Success Rate) até o pacote em questão."""
    _, taxa_teorica = calcula_toa_taxa_canal(spreading_factor, bandwidth_khz, coding_rate)
    taxa_calculada = round((taxa_teorica * psr_percentual) / 100,3)
    return taxa_teorica, taxa_calculada

# Define a pasta onde estão os dados brutos
PASTA_ARMAZENAMENTO = os.path.join("..", "3_N4_Armazenamento")
pasta_dados_brutos = os.path.join(PASTA_ARMAZENAMENTO, "Dados_Brutos")

while True:
    try:
            
        # Procura o último arquivo de dados brutos gravado no nível 4
        arquivo_entrada = ""
        if os.path.exists(pasta_dados_brutos):
            arquivos = os.listdir(pasta_dados_brutos)
            arquivos.sort()
            for nome in arquivos:
                if nome.endswith(".txt"):
                    arquivo_entrada = os.path.join(pasta_dados_brutos, nome)

        # Guard: ainda não existe nenhum arquivo de dados brutos disponível
        # (ex.: N5 subiu antes do N2_N3 gravar o primeiro arquivo da rodada).
        # Sem isso, o open() abaixo levantaria FileNotFoundError e derrubaria
        # o processo.
        if not arquivo_entrada:
            time.sleep(1)
            continue

        # Abre o arquivo de dados brutos
        try:
            arquivo = open(arquivo_entrada, "r")
            linhas = arquivo.readlines()
            arquivo.close()
        except (FileNotFoundError, PermissionError):
            # Pode acontecer de o arquivo estar sendo criado/renomeado pelo
            # N2_N3 exatamente no instante da leitura (condição de corrida).
            # Simplesmente tenta de novo no próximo ciclo.
            time.sleep(1)
            continue

        # Listas que guardam os valores calculados
        rssi_down = []
        rssi_up = []
        snr_down = []
        snr_up = []
        psr = []
        taxa_teorica_lista = []
        taxa_calculada_lista = []

        # Contadores usados para calcular a PSR
        total_pacotes = 0
        pacotes_recebidos = 0
        pacote_perdido = 0

        # Valores do ÚLTIMO pacote recebido (usados no print de status).
        # Inicializados como None/0 ANTES do loop para que sempre existam,
        # mesmo que nenhuma linha do arquivo tenha um pacote UL recebido
        # ainda (ex.: rodada recém-iniciada, ou 100% de perda de pacotes) —
        # isso evita o NameError que ocorria no print final.
        RSSI_DL = None
        RSSI_UL = None
        SNR_DL = None
        SNR_UL = None
        PSR = 0
        TAXA_TEORICA = None
        TAXA_CALCULADA = None

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
            else:
                pacote_perdido = pacote_perdido + 1

            # Calcula a PSR acumulada até este pacote
            PSR = (pacotes_recebidos/total_pacotes)*100
            psr.append(PSR)

            # ===================== TAXA DE CANAL (bps) =====================
            # Extrai SF (byte 0), Bandwidth (byte 1) e Coding Rate (byte 3) do
            # Pacote DL desta linha (bytes de configuração de rádio)
            try:
                sf_pacote = int(partes[2])
                bw_pacote = MAPA_BANDWIDTH.get(int(partes[3]), 125)
                cr_pacote = MAPA_CODINGRATE.get(int(partes[4]), 1)
                TAXA_TEORICA, TAXA_CALCULADA = calcula_taxa_canal(sf_pacote, bw_pacote, cr_pacote, PSR)
            except (ValueError, ZeroDivisionError):
                TAXA_TEORICA, TAXA_CALCULADA = None, None

            taxa_teorica_lista.append(TAXA_TEORICA)
            taxa_calculada_lista.append(TAXA_CALCULADA)

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

        # Grava a Taxa de Canal Teórica e a Taxa de Canal Calculada (real) em
        # arquivo temporário (uma linha por pacote, mesma ordem da PSR)
        f_taxa = open(arquivo_taxa,"w")
        for i in range(len(taxa_teorica_lista)):
            print(taxa_teorica_lista[i], taxa_calculada_lista[i], file=f_taxa)
        f_taxa.close()

        # Grava os Máximos e Mínimos em arquivo temporário. Cada campo é
        # gravado como "None" quando ainda não há dado disponível (nenhum
        # pacote recebido até o momento), e o Nível 6 trata essa string ao
        # ler o arquivo.
        f_stats = open(arquivo_stats,"w")
        print(rssi_down_min, rssi_down_max, rssi_up_min, rssi_up_max,
              snr_down_min, snr_down_max, snr_up_min, snr_up_max, pacote_perdido, file=f_stats)
        f_stats.close()

        print("Arquivo = ",arquivo_entrada," | Pacotes = ",total_pacotes," | Recebidos = ",pacotes_recebidos," | PSR = ",PSR,
              "| RSSI Downlink = ", RSSI_DL, "| RSSI Uplink = ", RSSI_UL, "| SNR Downlink = ", SNR_DL, "| SNR Uplink = ", SNR_UL,
              "| RSSI DL min/max = ", rssi_down_min, rssi_down_max, "| RSSI UL min/max = ", rssi_up_min, rssi_up_max,
              "| SNR DL min/max = ", snr_down_min, snr_down_max, "| SNR UL min/max = ", snr_up_min, snr_up_max,
              "| Taxa Canal Teórica (bps) = ", TAXA_TEORICA, "| Taxa Canal Calculada (bps) = ", TAXA_CALCULADA,
              "| Pacotes Perdidos = ", pacote_perdido)
        time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Ctrl + C] Interrompido pelo usuário.")
        
