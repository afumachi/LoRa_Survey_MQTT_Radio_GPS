void App_radio_receive_DL() {
  //Nesta camada são feitos os acionamentos ou ajustes enviados pela base no pacote de DL

  if (PacoteDL[16] == 1){
    digitalWrite(LED_AMARELO_PIN, HIGH);
    feedback_led_amarelo = 1;
  }
  if (PacoteDL[16] == 0){
    digitalWrite(LED_AMARELO_PIN, LOW);
    feedback_led_amarelo = 0;
  }

  App_radio_send_UL();  // Chama a função da camada de Aplicação de UL

}

void App_radio_send_UL() {
  // Neste ponto zeramos o pacote de UL para garantir que ele não está carregando nenhuma informação de comunicação anterior.
  for (int i = 0; i < TAMANHO_PACOTE; i++) {
    PacoteUL[i] = 0;
  }

  // Armazena as informações da Camada de Aplicação no PacoteUL[] que será enviado ao gateway LoRa

  // Feedback do estado do Led Amarelo
  if (feedback_led_amarelo == 1){
    PacoteUL[16] = 1;
  }
  else{
    PacoteUL[16] = 0;
  }

  // Lê o sensor LDR
  luminosidade = analogRead(LDR_PIN);
  PacoteUL[17] = (luminosidade/256);
  PacoteUL[18] = (luminosidade%256);
  
  PacoteUL[19] = 1; // Aqui está o tipo de Placa PKLoRa

  if (gps.location.isValid()) {
    // Latitude
    Serial.println("GPS VALIDO");    
    int32_t lat =  (gps.location.lat()) * 1e6;
    PacoteUL[20] = (lat >> 24) & 0xFF;
    PacoteUL[21] = (lat >> 16) & 0xFF;
    PacoteUL[22] = (lat >> 8)  & 0xFF;
    PacoteUL[23] =  lat        & 0xFF;

    // Longitude
    int32_t lon = (gps.location.lng()) * 1e6;
    PacoteUL[24] = (lon >> 24) & 0xFF;
    PacoteUL[25] = (lon >> 16) & 0xFF;
    PacoteUL[26] = (lon >> 8)  & 0xFF;
    PacoteUL[27] =  lon        & 0xFF;

    // Altitude (metros sem casas decimais, convertida explicitamente para inteiro de 16 bits)
    int16_t alt = (int16_t)gps.altitude.meters();
    PacoteUL[28] = (alt >> 8) & 0xFF; // Byte mais significativo (MSB)
    PacoteUL[29] = alt        & 0xFF; // Byte menos significativo (LSB)

  }

  // Limapa os dados do Display
  display.clearDisplay();
    
  // Escreve o Título Display
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("PKLoRa - Sensor GPS");
  //display.drawLine(0, 12, 128, 12, SSD1306_WHITE);
  display.drawLine(0, 11, 128, 11, SSD1306_WHITE);

  // Escreve valor LATITUDE e LONGITUDE GPS
  display.setTextSize(1);
  display.setCursor(0, 16);

  if (gps.location.isValid()) {
    display.print("LAT: "); display.println(gps.location.lat(), 5);
    display.print("LON: "); display.println(gps.location.lng(), 5);
    display.print("ALT: "); display.println(gps.altitude.meters(), 0);
  }
  else{
    display.println("GPS buscando...");
    display.println("Satelites......");

  }
  // Escreve o buffer na tela Oled

  Transp_radio_send_UL();
}

