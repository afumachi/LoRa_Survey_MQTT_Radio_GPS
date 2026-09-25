/*
  MoT LoRa Site Survey Versão Zero | WissTek IoT
  Última versão: Branquinho / Felipe / Anderson
  Hardware: PKLoRa ESP32
*/


#define PKLORA //#define PKLORA_ESP32
//#define AAFLORA // #define AAFLORA_ESP32

//=======================================================================
//                     1 - Bibliotecas
//=======================================================================

#include "Bibliotecas.h"  // Arquivo contendo declaração de bibliotecas e variáveis

// =====================================================================
//                     2 - Configurações MQTT
// =====================================================================
// Configurações do Broker Mosquitto (Usando o broker público oficial)
//const char* MQTT_BROKER = "test.mosquitto.org";

// Configurações do Broker HiveMQ (Usando o broker público oficial)
const char* MQTT_BROKER   = "broker.hivemq.com";

const int   MQTT_PORT     = 1883;

//const char* TOPIC_DL      = "mot_lora_mqtt_FEE23/gateway/downlink";
//const char* TOPIC_UL      = "mot_lora_mqtt_FEE23/gateway/uplink";

const char* TOPIC_DL      = "mot_lora_mqtt_IE350/gateway/downlink";  // Python → ESP32
const char* TOPIC_UL      = "mot_lora_mqtt_IE350/gateway/uplink";    // ESP32  → Python
String CLIENT_ID ;         // ID único no broker

// QoS usado nos dois sentidos (DL e UL). QoS1 = "at least once": o broker
// confirma o recebimento (PUBACK) e a biblioteca retransmite se necessário.
// Importante para o dado do cliente (luminosidade).
const int MQTT_QOS = 1;

// --- Objeto MQTT ---
MQTTClient mqttClient(256);   // buffer de 256 bytes (read/write)

// Cofiguração das redes Wi-Fi 2.4GHz disponíveis
void conectar_wifi_multi() {
  // Cadastre quantas redes você quiser (SSID, Senha)
  wifiMulti.addAP("MJCA_FUNDOS", "21092429MJC@");

	wifiMulti.addAP("2.4G COLETTI", "1145384609");


	wifiMulti.addAP("COLETTI_ext", "1145384609");
  wifiMulti.addAP("COLETTI_ADV_CRIS", "45384609");

	wifiMulti.addAP("aafwifi", "aaf12345678");
	wifiMulti.addAP("CHACARA BBC", "Ailton1960#");
	wifiMulti.addAP("Claro-EB66", "54b80a7deb66");


}

// uffer e flag para o pacote DL recebido via MQTT
volatile bool mqtt_dl_disponivel = false;
byte          mqtt_dl_payload[TAMANHO_PACOTE];

// Tempo de controle de standby Pacote_UL
unsigned long millis_standby_controle = 0; // Marca o instante em que pacote foi recebido
unsigned long time_out_lora_ul = 60000UL;  // 1 min. time out Pacote_UL

unsigned long millis_mqtt_controle = 0;
bool st_led_vermelho = 0;
//=======================================================================
// ------- 3 - Setup de inicialização ---------
//=======================================================================
// Inicializa as camadas
void setup() {
  //================= INICIALIZA SERIAL E MÓDULO RF95

  Serial.begin(115200);
  // Aguarda para estabilização da Serial
  delay(20);

  // declara Leds como saídas digital do ESP32
  pinMode(PIN_LED_VERMELHO, OUTPUT);
  pinMode(PIN_LED_VERDE, OUTPUT);
  digitalWrite(PIN_LED_VERMELHO, LOW);
  digitalWrite(PIN_LED_VERDE,    LOW);

  conectar_wifi_multi();

  // O wifiMulti.run() tenta conectar a uma das redes cadastradas
  // Ele retorna WL_CONNECTED quando consegue se conectar com sucesso
  while (wifiMulti.run() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("Wi-Fi conectado com sucesso!");
  Serial.print("Conectado na rede: ");
  Serial.println(WiFi.SSID());
  Serial.print("Endereço IP: ");
  Serial.println(WiFi.localIP());

  CLIENT_ID = "esp32_gateway+lora_" + String(WiFi.macAddress());
  CLIENT_ID.replace(":", "");

  // ---------- Inicia MQTT ----------
  mqttClient.begin(MQTT_BROKER, MQTT_PORT, wifiClient);
  mqttClient.onMessageAdvanced(mqtt_callback);
  conectar_mqtt();

  // --- Inicialização da Comunicação SPI entre o ESP32 e o Módulo LoRa RFM95 ---
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, NSS_PIN);
  delay(20);
  LoRa.setSPI(SPI);
  delay(20);

  // --- Inicialização da Comunicação LoRa em 915Mhz---
  LoRa.setPins(NSS_PIN, RST_PIN, DIO0_PIN);
  if (!LoRa.begin(FREQUENCY_IN_HZ)) {
    Serial.println("[Nó Sensor] Falha ao iniciar LoRa. Verifique conexões.");
    while (true); // Trava se o LoRa falhar
  }

  //  --- Atua Led vermelho  --- 
  digitalWrite(PIN_LED_VERMELHO, LOW); // LIGA LED VERMELHO - INDIFERENTE PARA O BOOT

  //  --- Atua Led verde  --- 
  digitalWrite(PIN_LED_VERDE, LOW);  // DESLIGA O LED VERDE - DEVE SER LOW DURANTE BOOT

  // Aguarda 1 segundo para estabilização
  delay(100);

  //  --- Pisca Led verde  --- Sucesso ao Iniciar 
  digitalWrite(PIN_LED_VERMELHO, HIGH);  // DESLIGA O LED VERDE - DEVE SER LOW DURANTE BOOT
  digitalWrite(PIN_LED_VERDE, HIGH);  // 
  delay(1000);
  digitalWrite(PIN_LED_VERMELHO, LOW); 
  digitalWrite(PIN_LED_VERDE, LOW);  //

  #ifdef loraCRC   // Habilitação do CRC do chip lora  (Configurado em bibliotecas.h)
    LoRa.enableCrc();
  #endif

} // FIM DO SETUP


//=======================================================================
//                     4 - Loop de repetição
//=======================================================================
// A função loop irá executar repetidamente
void loop() {

  // Mantém conexões ativas
  // No loop, você pode monitorar a conexão.
  // Se a rede cair, o wifiMulti.run() tenta reconectar automaticamente à melhor rede disponível.
  if (wifiMulti.run() != WL_CONNECTED) {
    Serial.println("Conexão perdida! Tentando reconectar...");
    delay(1000);
  }


  // Liga um LED a cada 500 [ms]
  unsigned long tempo_led_ms = 500UL;
  

  if (millis() - millis_mqtt_controle >= tempo_led_ms) {        

    st_led_vermelho = 1;
    // Zera contagem do tempo de controle MQTT para tempo de ESP32 rodando
    millis_mqtt_controle = millis(); 

  }
  else {
    st_led_vermelho = 0;
  }


  if (!mqttClient.connected()) {
    conectar_mqtt();
  }
  else{
    if (    st_led_vermelho == 1){
      digitalWrite(PIN_LED_VERMELHO, HIGH);
      digitalWrite(PIN_LED_VERDE, HIGH);
    }
    else{
      digitalWrite(PIN_LED_VERMELHO, LOW);
      digitalWrite(PIN_LED_VERDE, LOW);
    }
  }
  mqttClient.loop();   // processa envio/recebimento e handshakes de QoS1/2

  // Verifica se chegou pacote DL via MQTT e o envia pelo rádio LoRa
  Phy_mqtt_receive_DL();

  // Verifica se chegou pacote UL via rádio LoRa e o publica no broker
  Phy_radio_receive_UL();
  
  unsigned long tempo_standby_ul_ms = 2UL * time_out_lora_ul; // 2 min. sem Pacotes UL sobe para MAX  

  if (millis() - millis_standby_controle >= tempo_standby_ul_ms) {
    Serial.println("TEMPO SEM RECEBER PACOTES UL - Time-Out");
    Serial.println("Voltando a Configuração LoRa MDC");

    millis_standby_controle = millis();
    reset_gateway_para_setup_inicial(); // Timeout atingido → volta ao SETUP
  }  

}
