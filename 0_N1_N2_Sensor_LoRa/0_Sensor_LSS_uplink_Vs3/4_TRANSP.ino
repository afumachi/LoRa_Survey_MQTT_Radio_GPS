//================ RECEBE O PACOTE DE DL DA CAMADA DE REDE ========
void Transp_radio_receive_DL() { 

  //neste ponto pode ser implementado um controle relacionado ao recebimento não sequencial de pacotes de DL
  
  unsigned long tempo_pacoteDL_ms = (unsigned long)tempo_radio * 2UL * 1000UL; // 2x o valor recebido em MAC3_TEMPO

  if ((recebe_comando_nova_radio == 4) || (recebe_comando_nova_radio == 5)){ 

    if ((millis() - millis_contador_DL) >= tempo_pacoteDL_ms) {
      contador_perda_DL = contador_perda_DL + 1;  // Incrementa o contador de perda de pacote de DL
      Serial.println("[TRANSPORTE] PACOTES DL PERDIDOS: ");
      Serial.println(contador_perda_DL);
      millis_contador_DL = millis();
    }
    else{
      millis_contador_DL = millis();
    }
  }    
 
  App_radio_receive_DL();
}


//================ ENVIA O PACOTE DE UL À CAMADA DE REDE ========
void Transp_radio_send_UL() { 
  if (recebe_comando_nova_radio == 4){ 
    contadorUL = contadorUL + 1;  // Incrementa o contador de pacote de UL
  }

  PacoteUL[12] = contador_perda_DL/256; //PacoteDL[DL_COUNTER_MSB];
  PacoteUL[13] = contador_perda_DL%256; //PacoteDL[DL_COUNTER_LSB];

  PacoteUL[14] = contadorUL/256; // = (contadorUL >> 8) & 0xFF; 
  PacoteUL[15] = contadorUL%256; // = contadorUL & 0xFF;
  // neste ponto pode ser implementado um controle relacionado ao recebimento não sequencial de pacotes de DL

  Net_radio_send_UL();

}
