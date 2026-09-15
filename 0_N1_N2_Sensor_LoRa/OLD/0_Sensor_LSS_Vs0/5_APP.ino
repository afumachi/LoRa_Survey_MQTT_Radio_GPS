void App_radio_receive_DL() {
  //Nesta camada são feitos os acionamentos ou ajustes enviados pela base no pacote de DL

  if (PacoteDL[16] == 1){
    digitalWrite(PIN_LED_AMARELO, HIGH);
    feedback_led_amarelo = 1;
  }
  if (PacoteDL[16] == 0){
    digitalWrite(PIN_LED_AMARELO, LOW);
    feedback_led_amarelo = 0;
  }

  App_radio_send_UL();  // Chama a função da camada de Aplicação de UL

}

void App_radio_send_UL() {
  // Neste ponto zeramos o pacote de UL para garantir que ele não está carregando nenhuma informação de comunicação anterior.
  for (int i = 0; i < TAMANHO_PACOTE; i++) {
    PacoteUL[i] = 0;
  }

  // Armazene as informações no PacoteUL[] ele é que será enviado

  // Lê o sensor LDR

  luminosidade = analogRead(PIN_LDR); // trocar para o App_radio_send
  PacoteUL[17] = (luminosidade/256);
  PacoteUL[18] = (luminosidade%256);
  
  PacoteUL[19] = 1; // Aqui está o tipo de Placa PKLoRa

  // Feedback do estado do Led Amarelo
  if (feedback_led_amarelo == 1){
    PacoteUL[16] = 1;
  }
  else{
    PacoteUL[16] = 0;
  }
 
  Transp_radio_send_UL();
}

