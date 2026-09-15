
# ===== Bibliotecas =====
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
import math
import time
import struct
from time import localtime, strftime
import os
import random
import pandas as pd
import threading


# ========== Criação de Variáveis GLOBAIS =========================
global rssi_DL, rssi_UL, contador_UL, contador_DL, ultimo_pacote_DL, ultimo_pacote_UL, air_quality_indicator
global valor_inicial_spreadingfactor, valor_inicial_bandwidth, valor_inicial_codingrate, valor_inicial_potencia_radio
global valor_atual_spreadingfactor, valor_atual_bandwidth, valor_atual_codingrate, valor_atual_potencia_radio
global valor_anterior_spreadingfactor, valor_anterior_bandwidth, valor_anterior_codingrate, valor_anterior_potencia_radio
global valor_novo_spreadingfactor, valor_novo_bandwidth, valor_novo_codingrate, valor_novo_potencia_radio
global Tamanho_pacote, taxa_canal_teorica, taxa_canal_calculada, bitrate, perda_geral, st_cmd_led_amarelo
global medida_atual, numero_de_medidas, condicao_start, tempo_entre_medidas, perda_total, enlace_testado
global recebe_valor_spreadingfactor, recebe_valor_bandwidth, recebe_valor_codingrate, recebe_valor_potencia_radio
global comanda_mudar_radio, contador_pacote_DL, LSS_status, psr_geral, contador_reconfigura, confirma_mudar_radio
global psrDL_geral, contador_perda_DL, ID_gateway, ID_sensor, Pacote_DL, pacote_recebido, estado_mqtt, radio_configurado
global estado_lss


# ===== Configurações MQTT =====
BROKER        = "broker.hivemq.com"
#BROKER        = "test.mosquitto.org"
PORTA_MQTT    = 1883

# MODIFIQUE O TOPIC_DL E TOPIC_UL de acordo com SEU_NOME
TOPIC_DL      = "mot_lora_mqtt_A2F/gateway/downlink"   # Python publica → ESP32 assina
TOPIC_UL      = "mot_lora_mqtt_A2F/gateway/uplink"     # ESP32 publica  → Python assina

# QoS usado nos dois sentidos (DL e UL). QoS1 = "at least once": o broker
# confirma (PUBACK) e há retransmissão se a confirmação não chegar.
# Importante para o dado de luminosidade, que é a peça central do framework.
MQTT_QOS    = 1
estado_mqtt = 0

# ===== Variáveis globais =====
Tamanho_pacote = 20

# definições de teste: configurações importantes para a bateria de testes extraídas do arquivo de parâmetros
numero_de_medidas = 0
rota = [] # neste momento é um enlace ponto a ponto, que futuramente poderá ser usada para roteamento
condicao_start = 0
medida_atual = 0
enlace_testado = 0
pacote_recebido = 0
radio_configurado = 0
estado_lss = 0

#Camada Física
# Variáveis Auxiliares
recebe_valor_spreadingfactor = 12
recebe_valor_bandwidth = 125
recebe_valor_codingrate = 8
recebe_valor_potencia_radio = 20

# Configuração Inicial/Atual Rádio LoRa
valor_inicial_spreadingfactor = 12 # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
valor_inicial_bandwidth = 125 # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
valor_inicial_codingrate = 8 # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
valor_inicial_potencia_radio = 20 # TX Power = 1 a 17 ?

# Configuração Inicial/Atual Rádio LoRa
valor_atual_spreadingfactor = 12 # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
valor_atual_bandwidth = 125 # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
valor_atual_codingrate = 8 # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
valor_atual_potencia_radio = 20 # TX Power = 1 a 17 ?

# Configuração Anterior - Rádio LoRa
valor_anterior_spreadingfactor = 12 # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
valor_anterior_bandwidth = 125 # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
valor_anterior_codingrate = 8 # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
valor_anterior_potencia_radio = 20 # TX Power = 1 a 17 ?

# Configuração Nova Rádio LoRa recebida pelo Nível 6
valor_novo_spreadingfactor = 12 # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
valor_novo_bandwidth = 125 # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
valor_novo_codingrate = 8 # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
valor_novo_potencia_radio = 20 # TX Power = 1 a 17 ?

# Camada MAC
valor_tempo = 8
tempo_entre_medidas = 8 # original = 1 # alterado para 8 pior caso SF12/BW125k/CR8/pw20

# Adição variáveis de controle do ciclo de modif. configuração rádio LoRa
inicia_lora_site_survey = 0
comanda_mudar_radio = 0 # Comando de Downlink de mudança de configuração de rádio LoRa
confirma_mudar_radio = 0 # Recebe Uplink da Confirmação da mudança de rádio

# Camada Transporte
ID_gateway = 0
ID_sensor = 1

# Aplicação
Comando_LED_amarelo = 0

# Cria os pacotes de DL e UL
Pacote_DL = [0]*Tamanho_pacote
Pacote_UL = [0]*Tamanho_pacote

# Evento para sinalizar chegada de pacote UL =====
Pacote_UL_status = threading.Event()
Pacote_UL_payload = bytearray(Tamanho_pacote)

# Caminho da Pasta de armazenamento (Caminho Relativo)
PASTA_ARMAZENAMENTO = os.path.join("..", "3_N4_Armazenamento")
dir_nivel4 = os.path.join(os.path.dirname(__file__), '../3_N4_Armazenamento/Parametros/')

# Caminhos dos arquivos de armazenamento e leitura de parametros
caminho_parametros = os.path.join(PASTA_ARMAZENAMENTO, "Parametros")
caminho_dados = os.path.join(PASTA_ARMAZENAMENTO, "Dados_Brutos")

# os.makedirs com exist_ok=True substitui o 'if not os.path.exists' e cria toda a estrutura de uma vez
os.makedirs(caminho_dados, exist_ok=True)
os.makedirs(caminho_parametros, exist_ok=True)
caminho_led = os.path.join(caminho_parametros, "cmd_led_amarelo.txt")

#Atualiza arquivo de Parâmetros
pasta_parametros = os.path.join(dir_nivel4, 'PARAMETROS.txt')
parametros = open(pasta_parametros, 'w')
parametros.write("0\n0\n12\n125\n8\n20\n8\n0\n0\n") 
parametros.close()


arquivo_cmd_lora = 'cmd_lora.txt'
caminho_cmd_lora = os.path.join(caminho_parametros, arquivo_cmd_lora)
parametros_cmd = open(caminho_cmd_lora, 'w')
parametros_cmd.write("0\n0\n") 
parametros_cmd.close()


# Conteúdo de 2 linhas para escrever
linhas_conteudo = [
    "linha1: parametros_radio_01\n",
    "linha2: parametros_radio_02\n"
]

# ===== Callbacks MQTT
def on_connect(client, userdata, flags, reason_code, properties):
    global estado_mqtt
    if reason_code == 0:
        print("[MQTT] Conectado ao Broker MQTT com sucesso.")
        client.subscribe(TOPIC_UL, qos=MQTT_QOS)
        print(f"[MQTT] Inscrito no tópico: {TOPIC_UL} (QoS{MQTT_QOS})")
        estado_mqtt = 1
    else:
        print(f"[MQTT] Falha na conexão. Código: {reason_code}")
        estado_mqtt = 0
        client.reconnect()

def on_publish(client, userdata, mid, reason_code, properties):
    """Confirmação de entrega (PUBACK) do pacote DL publicado em QoS1."""
    #print(f"[MQTT] PUBACK recebido para mid={mid} (pacote DL confirmado pelo broker).")

def on_message(client, userdata, msg):
    """Callback disparado ao receber pacote UL vindo do ESP32."""
    global Pacote_UL_payload
    payload = msg.payload
    if len(payload) >= Tamanho_pacote:
        Pacote_UL_payload = bytearray(payload[:Tamanho_pacote])
        Pacote_UL_status.set()   # Sinaliza que chegou um pacote válido

def on_disconnect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        print(f"[MQTT] Desconectado inesperadamente (rc={reason_code}). Tentando reconectar...")      
        # Utilizando loop_start() neste código, caso NÃO desmarque a linha abaixo:
        estado_mqtt = 0
        client.reconnect()
        

# ===== Inicialização do cliente MQTT =====
client = mqtt.Client(CallbackAPIVersion.VERSION2)
client.on_connect    = on_connect
client.on_message    = on_message
client.on_disconnect = on_disconnect
client.on_publish    = on_publish

print("[MQTT] Conectando ao broker MQTT - porta 1883...")
client.connect(BROKER, PORTA_MQTT, keepalive=60)
client.loop_start()   # Thread de fundo para receber mensagens

# Aguarda conexão ser estabelecida com BROKER
time.sleep(2)

# Garante que os pacotes de DL e UL estão com valor 0
for i in range(Tamanho_pacote):
   Pacote_DL[i] = 0
   Pacote_UL[i] = 0

# =======================================================

# Criação do arquivo de CMD LED AMARELO
CMD_LED_FILE = os.path.join(dir_nivel4, 'cmd_led_amarelo.txt')
if not os.path.exists(CMD_LED_FILE):
    with open(CMD_LED_FILE, "w") as f:
        f.write("0")


def ler_cmd_led_amarelo():
    try:
        with open(CMD_LED_FILE, "r") as f:
            val = f.read().strip()
            return int(val) if val in ("0", "1") else 0
    except Exception as e:
        print(f"[AVISO] Não foi possível ler {CMD_LED_FILE}: {e}. Usando LED=0.")
        return 0



#========== FUNÇÃO QUE RECONFIGURA RÁDIO LORA ================
def muda_radio_lora():
   global comanda_mudar_radio, inicia_lora_site_survey, valor_atual_spreadingfactor, valor_atual_bandwidth, valor_atual_codingrate, valor_atual_potencia_radio
   global valor_anterior_spreadingfactor, valor_anterior_bandwidth, valor_anterior_codingrate, valor_anterior_potencia_radio, valor_novo_spreadingfactor
   global valor_novo_bandwidth, valor_novo_codingrate, valor_novo_potencia_radio, LSS_status, contador_reconfigura, confirma_mudar_radio

   LSS_status = 3 # Status de mudança de rádio
   contador_reconfigura = 0

   while (confirma_mudar_radio < 3):
       comanda_mudar_radio = 1
       cmd_lora()
       
       contador_reconfigura = contador_reconfigura + 1
       if contador_reconfigura >= 3:
           contador_reconfigura = 0
           perda_enlace()

   if (confirma_mudar_radio == 3):
       inicia_lora_site_survey = 1
       valor_anterior_spreadingfactor = valor_atual_spreadingfactor
       valor_anterior_bandwidth = valor_atual_bandwidth
       valor_anterior_codingrate = valor_atual_codingrate
       valor_anterior_potencia_radio = valor_atual_potencia_radio
       valor_atual_spreadingfactor = valor_novo_spreadingfactor
       valor_atual_bandwidth = valor_novo_bandwidth
       valor_atual_codingrate = valor_novo_codingrate
       valor_atual_potencia_radio = valor_novo_potencia_radio 
       LSS_status = 0


#========== INICIA ENVIOS DE PACOTES VIA RÁDIO LORA ================
def cmd_lora():
   downlink()
   time.sleep(8)
   uplink()

#========== DOWNLINK ================
def downlink():
   global rssi_DL, rssi_UL, contador_UL, contador_DL, ultimo_pacote_DL, ultimo_pacote_UL
   global air_quality_indicator, Pacote_DL, medida_atual, comanda_mudar_radio, estado_lss

   # Limpa o pacote para garantir que não tem lixo
   for i in range(Tamanho_pacote):
       Pacote_DL[i] = 0

   # Camada de Aplicação
   Comando_LED_amarelo = ler_cmd_led_amarelo()
   Pacote_DL[16] = Comando_LED_amarelo

   # Camada de Transporte
   Pacote_DL[12] = int(medida_atual/256)
   Pacote_DL[13] = int(medida_atual%256)
   
   # Camada de Rede
   Pacote_DL[8] = ID_sensor
   Pacote_DL[10] = ID_gateway

   # Camada MAC
   Pacote_DL[4] = int(numero_de_medidas/256)  # MSB
   Pacote_DL[5] = int(numero_de_medidas%256)  # LSB
   Pacote_DL[6] = tempo_entre_medidas
   Pacote_DL[7] = comanda_mudar_radio
   estado_lss = comanda_mudar_radio
   print("### DOWNLINK ### MÁQUINA ESTADO LORA: ", comanda_mudar_radio)


   with open(caminho_cmd_lora, 'r') as f:
       linhas = f.readlines()

   # Altera a 1ª linha (índice 0)
   linhas[0] = f"{estado_lss}\n"

   with open(caminho_cmd_lora, 'w') as f:
       f.writelines(linhas)


   # Camada PHY Física

   # Converte Bandwidth para envio em Byte [0-255]
   if (valor_novo_bandwidth == 125):
      valor_BW = 1
   elif (valor_novo_bandwidth == 250):
      valor_BW = 2
   elif (valor_novo_bandwidth == 500):
      valor_BW = 3
      
   Pacote_DL[0] = valor_novo_spreadingfactor
   Pacote_DL[1] = valor_BW
   Pacote_DL[2] = valor_novo_codingrate
   Pacote_DL[3] = valor_novo_potencia_radio

   # -------- Publica pacote DL no broker MQTT --------
   Pacote_UL_status.clear()
   result = client.publish(TOPIC_DL, bytes(Pacote_DL), qos=MQTT_QOS)

   # AGUARDA ACK DO BROKER - QoS1
   if client.is_connected():
      try:
         # Aguarda confirmação da publicação do Pacote DL pelo retorno do result client.publish(timeout = tempo entre pacotes)
         result.wait_for_publish(timeout=tempo_entre_medidas)
         print(f"Pacote [DL] {medida_atual:03d} publicado no broker | LED={Comando_LED_amarelo}")
      except RuntimeError as e:
         print(f"[MQTT Erro] Falha ao aguardar publicação: {e} timeout > tempo entre os pacotes")
         # Aqui você pode tratar a queda: ex. salvar o pacote ou esperar reconectar
      except Exception as e:
         print(f"[Erro] Outro erro ocorreu: {e}")
   else:
      print("[MQTT] Não foi possível publicar. Cliente desconectado.")
      # Inserir Lógica de contingência se o cliente já estiver deslogado
      estado_mqtt = 0
      medidas = 0
      client.disconnect()
      print("[MQTT] Reconectando ao broker...")
      client.disconnect()
      client.connect(BROKER, PORTA_MQTT, keepalive=60)
      client.loop_start()   # Thread de fundo para receber mensagens       
      client.reconnect()


#========== UPLINK ==================
def uplink():
   global perda_geral, rssi_DL, rssi_UL, contador_UL, ultimo_pacote_DL
   global Pacote_UL, luminosidade, confirma_mudar_radio, snr_UL, snr_DL, st_cmd_led_amarelo
   global perda_total, contador_pacote_DL, contador_DL, medida_atual, numero_de_medidas
   global temperatura, umidade, latitude, longitude, altitude, contador_perda_DL, pacote_recebido

   # ======== COLETA UPLINK NO BROKER ========
   # Aguarda novo pacote UL publicado pelo Gateway (timeout = Tempo_entre_pacotes)
   Pacote_UL_novo = Pacote_UL_status.wait(timeout=tempo_entre_medidas)

   if Pacote_UL_novo:
      Pacote_UL = Pacote_UL_payload         
      if len(Pacote_UL) == Tamanho_pacote:
         # print('Pacote = ',medida_atual,' | Pacote UL recebido | LED = ',Comando_LED_amarelo)
                          
         # Camada MAC
         confirma_mudar_radio = Pacote_UL[7]

         with open(caminho_cmd_lora, 'r') as f:
             linhas2 = f.readlines()

         # Altera a 2ª linha (índice 1)
         linhas2[1] = f"{confirma_mudar_radio}\n"

         with open(caminho_cmd_lora, 'w') as f:
             f.writelines(linhas2)
         
         pacote_recebido = 1
   else: 
      pacote_recebido = 0


#============================================================================================================================

       
def teste_enlace():
    global confirma_mudar_radio, comanda_mudar_radio, medida_atual, numero_de_medidas, condicao_start, LSS_status
    LSS_status = 2
    comanda_mudar_radio = 3
    time.sleep(0.5)
    cmd_lora()
    comanda_mudar_radio = 0

def perda_enlace():
    global confirma_mudar_radio, comanda_mudar_radio, medida_atual, numero_de_medidas, condicao_start, perda_geral
    global valor_novo_spreadingfactor, valor_novo_bandwidth, valor_novo_codingrate, valor_novo_potencia_radio, LSS_status

    perda_geral = 0
    print("### PERDA DE ENLACE LORA ### SET GATEWAY LORA TO BEST DISTANCE CONFIGURATION")
    comanda_mudar_radio = 10
    cmd_lora()
    time.sleep(0.5)
    if (confirma_mudar_radio == 10):
        print("")
        print("### RECUPERAÇÃO DE ENLACE LORA ### GATEWAY LORA ON BEST DISTANCE CONFIGURATION")
        teste_enlace()
        time.sleep(0.5)

        if (confirma_mudar_radio == 4):
            perda_geral = 0
            print("### PERDA DE ENLACE LORA ### ENLACE OK")
            valor_novo_spreadingfactor = recebe_valor_spreadingfactor
            valor_novo_bandwidth = recebe_valor_bandwidth
            valor_novo_codingrate = recebe_valor_codingrate
            valor_novo_potencia_radio = recebe_valor_potencia_radio     

            print("### PERDA DE ENLACE LORA ### APLICANDO MUDANÇA DE CONFIG RADIO LORA ###", comanda_mudar_radio)
            comanda_mudar_radio = 1
            confirma_mudar_radio = 1
            muda_radio_lora()

            comanda_mudar_radio = 0
            confirma_mudar_radio = 0
            LSS_status = 1

        else:
            print("################## Medições LoRa Site Survey finalizadas ##################")
            condicao_start = 0
            medida_atual = 0
            comanda_mudar_radio = 0
            confirma_mudar_radio = 0
            perda_geral = 0
            LSS_status = 0                   


# ===== Loop principal: repete pedindo número de medidas =====
print("\n========== Gateway LoRa - Comunicação MQTT ==========")
try:
    while True:

      # Caso MQTT desconectado - Reconectar
      if estado_mqtt != 1:
         client.disconnect()
         client.connect(BROKER, PORTA_MQTT, keepalive=60)
         client.loop_start()   # Thread de fundo para receber mensagens
         
      # Leitura constante do arquivo de parâmetros do Usuário Nível 6
      path_param = os.path.join(dir_nivel4, 'PARAMETROS.txt')
      if os.path.exists(path_param):
         Parametros = open(path_param, 'r')
         line = Parametros.readline()
         if len(line) > 0: condicao_start = int(line)
         line = Parametros.readline()
         if len(line) > 0: numero_de_medidas = int(line)
         line = Parametros.readline()
         if len(line) > 0: recebe_valor_spreadingfactor = int(line)
         line = Parametros.readline()
         if len(line) > 0: recebe_valor_bandwidth = int(line)
         line = Parametros.readline()
         if len(line) > 0: recebe_valor_codingrate = int(line)
         line = Parametros.readline()
         if len(line) > 0: recebe_valor_potencia_radio = int(line)
         line = Parametros.readline()
         if len(line) > 0: valor_tempo = int(line)
         Parametros.close()


      valor_novo_spreadingfactor = recebe_valor_spreadingfactor
      valor_novo_bandwidth = recebe_valor_bandwidth
      valor_novo_codingrate = recebe_valor_codingrate
      valor_novo_potencia_radio = recebe_valor_potencia_radio     
       
      if (condicao_start == 1):
                       
          if (enlace_testado == 0):
             print("### LSS - TESTE ENLACE LORA ###")
             teste_enlace()
             enlace_testado = 1
             time.sleep(0.5)
             
             if (confirma_mudar_radio == 4):
                 print("### LSS - TESTE ENLACE LORA REALIZADO COM SUCESSO ###")
                 comanda_mudar_radio = 0
                 confirma_mudar_radio = 0
                 LSS_status = 1
                 perda_total = 0
                 perda_geral = 0             
             else:
                 print("### LSS - FALHA TESTE ENLACE LORA - REFAZENDO TESTE... ###")
                 teste_enlace()
                 enlace_testado = 1
                 time.sleep(0.5)
                 if (confirma_mudar_radio == 4):
                     print("### LSS - TESTE ENLACE LORA REALIZADO COM SUCESSO ###")
                     comanda_mudar_radio = 0
                     confirma_mudar_radio = 0
                     LSS_status = 1
                     perda_total = 0
                     perda_geral = 0
                 else:
                     print("### LSS - ENLACE LORA PERDIDO - FUNÇÃO PERDA DE ENLACE ###")
                     perda_enlace()
                     comanda_mudar_radio = 0
                     confirma_mudar_radio = 0
                     perda_total = 0
                     perda_geral = 0

          tempo_entre_medidas = valor_tempo
          
          
          if (medida_atual == 0):
              
             LSS_status = 3
             comanda_mudar_radio = 1
             confirma_mudar_radio = 1
             print("### LSS - Mudança de Configuração de Rádio Detectada")
             print("### LSS - Entrando em Modo Muda Config. Rádio LoRa ### ", comanda_mudar_radio)
             muda_radio_lora()
             radio_configurado = 1
             inicia_lora_site_survey = 1
             comanda_mudar_radio = 4
             confirma_mudar_radio = 0
             LSS_status = 1
             print("################## LSS - Iniciando Medições LoRa #################")
             # Gera o nome do arquivo com o novo caminho
             filename1 = strftime(os.path.join(caminho_dados, "Rodada_Teste_%Y_%m_%d_%H-%M-%S.txt"))
   
             Log_dados = open(filename1, 'w')
             print("Arquivo de log: %s" % filename1)
             Cabecalho = 'Time stamp,Contador,DL_B0,DL_B1,DL_B2,DL_B3,DL_B4,DL_B5,DL_B6,DL_B7,DL_B8,DL_B9,DL_B10,DL_B11,DL_B12,DL_B13,DL_B14,DL_B15,DL_B16,DL_B17,DL_B18,DL_B19,UL_B0,UL_B1,UL_B2,UL_B3,UL_B4,UL_B5,UL_B6,UL_B7,UL_B8,UL_B9,UL_B10,UL_B11,UL_B12,UL_B13,UL_B14,UL_B15,UL_B16,UL_B17,UL_B18,UL_B19'
             print(Cabecalho,file=Log_dados)             
             time.sleep(1)
          else:
             comanda_mudar_radio = 4 
             confirma_mudar_radio = 0
             LSS_status = 1
             

          if (medida_atual < numero_de_medidas):
              LSS_status = 1
              tempo_entre_medidas = valor_tempo
             
              medida_atual = medida_atual + 1
              print("### LSS - Medida: ",medida_atual, "de ",numero_de_medidas)

              if ((medida_atual) == (numero_de_medidas)):
                  comanda_mudar_radio = 5  

              # =============== Camada de aplicação DL
              Comando_LED_amarelo = 0  # Inicia apagado
              # ================ Camada de Transporte DL
              Contador_pkt_DL = 0
              perda_PK_RX = 0
              # ================ Camada de Rede DL
              #ID_sensor = input("Identificação do sensor = ")
              ID_sensor = 1
              #ID_gateway = input ("Identificação do gateway =")
              ID_gateway = 0
              # ================ Camada MAC DL
              #Tempo_entre_pacotes = input("Tempo entre pacotes (s) =")
              Tempo_gasto = 0

              # ================ Envio de pacote de DL
              try:
              # ===================== LOOP DE ENVIO DE PACOTES =============
                    Tempo_inicio_pacote = time.time()
                    
                    downlink() 
                                          
                    time.sleep(tempo_entre_medidas/2)

                    uplink()

                    if (pacote_recebido == 1):
                        
                        Dados_DL = ''
                        Dados_UL = ''
                        #Prepara os dados dos pacotes de Downlink e Uplink para serem impressos
                        for i in range(Tamanho_pacote):
                           if i == 0:
                              Dados_DL = str(Pacote_DL[i])
                              Dados_UL = str(Pacote_UL[i])
                           else:
                              Dados_DL = Dados_DL + ', ' + str(Pacote_DL[i])
                              Dados_UL = Dados_UL + ', ' + str(Pacote_UL[i])
                        Tempo = time.asctime()
                        print(Tempo + ', ' + str(medida_atual) + ', Downlink: ' + Dados_DL + ' Uplink: ' + Dados_UL)
                        # Grava Pacotes
                          
                        Dados_log = Tempo + ',' + str(medida_atual) + ',' + Dados_DL + ',' + Dados_UL
                        print(Dados_log,file=Log_dados)
                        Log_dados.flush()

                    else:

                       perda_PK_RX += 1
                       print('Cont = ', medida_atual, ' PERDEU PACOTE ')
                       Dados_DL = ''
                       Dados_UL = ''
                       for i in range(Tamanho_pacote):
                          if i == 0:
                             Dados_DL = str(Pacote_DL[i])
                             Dados_UL = '9'
                          else:
                             Dados_DL = Dados_DL + ', ' + str(Pacote_DL[i])
                             Dados_UL = Dados_UL + ', 9'
                       Tempo = time.asctime()
                       print(Tempo + ', ' + str(medida_atual) + ', Downlink: ' + Dados_DL + ' Uplink: ' + Dados_UL)

                       # Grava Pacotes
                       Dados_log = Tempo + ',' + str(medida_atual) + ',' + Dados_DL + ',' + Dados_UL
                       print(Dados_log,file=Log_dados)
                       Log_dados.flush()
                    

                    Tempo_gasto = time.time() - Tempo_inicio_pacote
               

              except:
                 Log_dados.close()
                 print('[LoRa] Fim da Execução')

             
          else:
             print("################## Medições LoRa Site Survey finalizadas ##################")
             print('Pacotes enviados = ',medida_atual,' Pacotes perdidos = ',perda_PK_RX)
             print('Tempo Entre Pacotes = ',Tempo_gasto)
             Log_dados.close()
             condicao_start = 0
             medida_atual = 0
             comanda_mudar_radio = 0
             radio_configurado = 0
             inicia_lora_site_survey = 0
             confirma_mudar_radio = 0
             enlace_testado = 0
             perda_geral = 0
             tempo_entre_medidas = 8
             perda_total = 0
             contador_DL = 0
             contador_UL = 0
             LSS_status = 0
             contador_perda_DL = 0
             estado_lss = 0
             #Atualiza arquivo de Parâmetros
             path_param = os.path.join(dir_nivel4, 'PARAMETROS.txt')
             Parametros = open(path_param, 'w')
             Parametros.write("0\n0\n12\n125\n8\n20\n8\n0\n0\n") 
             Parametros.close()
      
      else:
         medida_atual = 0
         perda_geral = 0
         condicao_start = 0
         radio_configurado = 0
         comanda_mudar_radio = 0
         confirma_mudar_radio = 0
         enlace_testado = 0
         perda_geral = 0
         perda_total = 0
         contador_DL = 0
         contador_perda_DL = 0
         contador_UL = 0
         tempo_entre_medidas = 8
         LSS_status = 0
         estado_lss = 0
         print("LSS pausado")
         time.sleep(2)

         
# Interrompe a aplicação N2_N3 e a conexão com MQTT
except KeyboardInterrupt:
   print("\n[Ctrl + C] Interrompido pelo usuário.")
   Log_dados.close()
   print('[LoRa] Fim da Execução')
   client.loop_stop()
   client.disconnect()
   print("[MQTT] Desconectado do broker.")
   
   path_param = os.path.join(dir_nivel4, 'PARAMETROS.txt')
   Parametros = open(path_param, 'w')
   Parametros.write("0\n0\n12\n125\n8\n20\n8\n0\n0\n") 
   Parametros.close()   
finally:
   client.loop_stop()
   client.disconnect()
   print("[MQTT] Desconectado do broker.")
