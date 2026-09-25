/*
  MoT LoRa Site Survey Versão Configura Rádio | WissTek IoT
  Última versão: Branquinho / Felipe / Anderson
  Hardware: PKLoRa ESP32
*/

/*
// Máquina de Estado_DL:
// 10 => Estado Inicial Sem Enlace - Sem Recepção de DL - Sem request UL (standy-by)
// confirma_novo_radio_base = 10; // AAF 17-09 inicio do Estado_DL == 10

// 1 => Mudança de Rádio request UL

// 3 => Teste de Enlace request UL

// 4 => LSS request UL

// 5 => LSS último Pacote request UL
// após send UL, confirma_novo_radio_base = 10;

*/

// Hardware - Configuração da Seleção do Tipo de Hardware (ESP32 ou NODEMCU)
// Remova o comentário da linha referente à placa que você está usando no momento e comente a outra

//#define PKLORA_ESP32 //#define PKLORA_NODEMCU
#define PKLORA_NODEMCU // #define PKLORA_ESP32

//=======================================================================
//                     1 - Bibliotecas
//=======================================================================
#include <SPI.h> // A SPI é usada para conectar o ESP32 com o RFM95
#include <LoRa.h> // Biblioteca do RFM95
#include "Bibliotecas.h"  // Arquivo contendo declaração de bibliotecas e variáveis

//=======================================================================
//                     2 - Variáveis e Mapeamento
//=======================================================================
/*
// ============= Pinagem na placa da PK-LoRa da ligação do RFM95 com o ESP32
#define SCK_PIN    5
#define MISO_PIN  19
#define MOSI_PIN  27
#define NSS_PIN   18
#define RST_PIN   14
#define DIO0_PIN  26
#define DIO1_PIN  35
#define DIO2_PIN  34
*/
// ============= CAMADA FÍSICA
// Parâmetros do LoRa
#define FREQUENCY_IN_HZ       903E6    // LoRa Frequency
#define txPower               14       // TX power in dBm, defaults to 17
#define spreadingFactor       12       // ranges from 6-12,default 7
#define signalBandwidth       125E3    // signal bandwidth in Hz
#define codingRateDenominator 8        // denominator of the coding rate

//#define loraCRC                // Habilita ou disabilita o uso CRC, por padrão o CRC não é usado.

// Váriáveis utilizadas no código
int RSSI_dBm_DL; // Variável com a potência rádio recebida (RSSI) em dBm
int RSSI_DL;     // Variável de mapeamento da RSSI em um valor de 0 a 255 para colocar no pacote

float SNR_DL_bruto;   // Variável com a relação sinal ruído
uint8_t SNR_DL;           // Variável inteira para enviar a SNR, que será convertida para a SNR original no Python

// ============== CAMADA MAC
#define TAMANHO_PACOTE 30
byte PacoteDL[TAMANHO_PACOTE];
byte PacoteUL[TAMANHO_PACOTE];

// ============= CAMADA DE REDE
// Identificação do sensor e tamanho de pacote
int ID_sensor = 2; // Variável de iIdentificação do sensor que está no pacote de DL byte 8
int ID_gateway = 0;    // Variável com o ID_gateway que estará no pacote de DL byte 10

// ============== CAMADA DE TRANSPORTE
int contador_pkt_DL = 0; // Variável para o contador de pacotes de DL
int contador_pkt_UL = 0; // Variável para o contador de pacotes de UL
uint16_t contadorUL = 0;
uint16_t contadorDL = 0;
uint16_t contadorSS = 0;

int luminosidade; // Variável que vai receber o valor da luminosidade entre 0 e 4095 - ADC 12 bits
uint8_t feedback_led_amarelo = 0;

//=======================================================================
// ------- 3 - Setup de inicialização ---------
//=======================================================================
// Inicializa as camadas
void setup() {

  Serial.begin(115200);
  delay(200);
  Serial.println("--- Iniciando Nó Sensor LoRa ---");

  // --- Inicialização de I/O ---
  pinMode(LED_VERMELHO_PIN, OUTPUT);
  pinMode(LED_VERDE_PIN, OUTPUT);
  
  #if defined(PKLORA_ESP32)
    pinMode(BOTAO_PIN, INPUT); 
    pinMode(LED_AMARELO_PIN, OUTPUT);
    // Configuração ADC para o LDR
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);
  #endif

  pinMode(LDR_PIN, INPUT);

  // Garante que os LEDs iniciem desligados
  digitalWrite(LED_VERMELHO_PIN, LOW);
  digitalWrite(LED_VERDE_PIN, LOW);

  #if defined(PKLORA_ESP32)
    digitalWrite(LED_AMARELO_PIN, LOW);

    // GPS Serial: Baud 9600, Pins: RX=16, TX=17
    SerialGPS.begin(9600, SERIAL_8N1, 16, 17);

    // Initialize I2C with your specific pins (SDA = 21, SCL = 22)
    Wire.begin(21, 22);
    delay(100);

    // Initialize OLED display
    if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { // 0x3C is common I2C address
      Serial.println(F("SSD1306 allocation failed"));
      for(;;); 
    }
    
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    delay(100);

    // --- Inicialização Módulo RF95 (LoRa) ---

    // 1. Remapeia e inicializa o barramento SPI com os pinos do seu Kit
    SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, NSS_PIN);
  #endif
  
  // 2. Informa à biblioteca LoRa os pinos de controle
  LoRa.setPins(NSS_PIN, RST_PIN, DIO0_PIN);

  if (!LoRa.begin(FREQUENCY_IN_HZ)) {
    Serial.println("Erro ao iniciar módulo RFM95");
  }

  LoRa.setTxPower(txPower);
  LoRa.setSpreadingFactor(spreadingFactor);
  LoRa.setSignalBandwidth(signalBandwidth);
  LoRa.setCodingRate4(codingRateDenominator);
 
  Serial.println("LoRa Inicializado com Sucesso!");

  #if defined(PKLORA_ESP32)
    // Limpa o Display
    display.clearDisplay();
      
    // Escreve o Título Display
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("PKLoRa Site Survey");
    display.drawLine(0, 12, 128, 12, SSD1306_WHITE);    

    // Escreve valor do LDR
    display.setTextSize(1);
    display.setCursor(0, 17);
    display.println("PKLoRa Inicializado");
    display.println("");  
    display.setTextSize(2);
    display.println("SUCESSO!"); 

    // Escreve o buffer na tela Oled
    display.display();
  #endif


  #ifdef loraCRC   // Habilitação do CRC do chip lora  (Configurado em bibliotecas.h)
    LoRa.enableCrc();
  #endif

  // Pisca o LED Verde para indicar inicialização bem-sucedida
  digitalWrite(LED_VERDE_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_VERDE_PIN, LOW);

} // FIM DO SETUP

//=======================================================================
//  ------------ 4 - Loop de repetição ------------
//=======================================================================
// A função loop irá executar repetidamente
void loop() {
    
  // --- Controle de timeout do Comando 4 ---
  // Executado a cada iteração do loop, independente de novo pacote chegar
  if (controle_ativo) {
    unsigned long tempo_limite_ms = (unsigned long)tempo_radio * 100UL * 1000UL; // 10x o valor recebido em MAC3_TEMPO

    if (millis() - millis_inicio_controle >= tempo_limite_ms) {
      reset_para_setup_inicial(); // Timeout atingido → volta ao SETUP
    }
    millis_inicio_controle = millis();
  }


  unsigned long tempo_standby_ms = 10UL * time_out_lora_dl; // 10 min. sem Pacotes DL sobe para MAX  

  if ((millis() - millis_standby_controle >= tempo_standby_ms)) {
    Serial.println("TEMPO SEM RECEBER PACOTES - Time-Out");
    Serial.println("Voltando a Configuração LoRa MDC");
    millis_standby_controle = millis();
    reset_para_setup_inicial(); // Timeout atingido → volta ao SETUP
  }     


  #if defined(PKLORA_ESP32)
    // Lê os caracteres do GPS a cada 200 [ms]
    unsigned long tempo_sensores_ms = 200UL; // 200 ms

    if (millis() - millis_gps_controle >= tempo_sensores_ms) {        
      updateGPS(); // Atualiza / Lê GPS
      //Serial.println("FUNÇÃO UPDATE GPS");  
      // Zera contagem do tempo de controle GPS para tempo de ESP32 rodando
      millis_gps_controle = millis(); 
    }
  #endif

  Phy_radio_receive_DL(); // Função que recebe os pacotes pelo rádio

/*
  unsigned long tempo_pacoteDL_ms = (unsigned long)tempo_radio * 1UL * 1500UL; // 1,5x o valor recebido em MAC3_TEMPO


  if ((confirma_novo_radio_base != 10) & ((millis() - millis_contador_DL) >= tempo_pacoteDL_ms)) {
    millis_contador_DL = millis();
    Perda_DL = 1;
    Transp_radio_receive_DL();
  }

*/



}

