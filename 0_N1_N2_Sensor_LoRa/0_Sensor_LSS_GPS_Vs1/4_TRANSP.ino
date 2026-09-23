//================ RECEBE O PACOTE DE DL DA CAMADA DE REDE ========
void Transp_radio_receive_DL() { 

  //confirma_novo_radio_base = PacoteDL[7]; // Caso Pacote for para este Nó Sensor
  //Serial.print("confirma_novo_radio_base = "); // Para Debug
  //Serial.println(confirma_novo_radio_base); // // Para Debug
  //neste ponto pode ser implementado um controle relacionado ao recebimento não sequencial de pacotes de DL
  /*
  
  
  if (Perda_DL == 1) //== 4)  || (confirma_novo_radio_base == 5)){ 
    millis_contador_DL = millis();
    contador_perda_DL = contador_perda_DL + 1;  // Incrementa o contador de perda de pacote de DL
    Serial.println("[TRANSPORTE] PACOTES DL PERDIDOS: ");
    Serial.println(contador_perda_DL);
    Perda_DL = 0;
    App_radio_send_UL();
  }  
  */  

  App_radio_receive_DL();
}


//================ ENVIA O PACOTE DE UL À CAMADA DE REDE ========
void Transp_radio_send_UL() { 
  if ((recebe_comando_nova_radio == 4) || (recebe_comando_nova_radio == 5)){ 
    contadorUL = contadorUL + 1;  // Incrementa o contador de pacote de UL
  }

  PacoteUL[12] = contador_perda_DL/256; //PacoteDL[DL_COUNTER_MSB];
  PacoteUL[13] = contador_perda_DL%256; //PacoteDL[DL_COUNTER_LSB];

  PacoteUL[14] = contadorUL/256; // = (contadorUL >> 8) & 0xFF; 
  PacoteUL[15] = contadorUL%256; // = contadorUL & 0xFF;
  // neste ponto pode ser implementado um controle relacionado ao recebimento não sequencial de pacotes de DL

  display.setTextSize(1);
  display.setCursor(0, 38);
  display.print("Pkt_UL : ");
  display.setTextSize(1);
  display.println(contadorUL, 1); 

  // Escreve o buffer na tela Oled
  //display.display();  

  Net_radio_send_UL();

}
