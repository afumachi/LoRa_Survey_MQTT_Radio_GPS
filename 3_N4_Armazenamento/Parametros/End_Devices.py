import csv

# -------------------------------------------------------------------
# 1. Dados dos 3 End Devices LoRa
# -------------------------------------------------------------------
end_devices = [
    {
        "endereco_rede": 1,
        "spreading_factor": 12,
        "bandwidth": 125,      # em kHz
        "coding_rate": 8,
        "potencia_tx": 20      # em dBm
    },
    {
        "endereco_rede": 2,
        "spreading_factor": 12,
        "bandwidth": 125,      # em kHz
        "coding_rate": 8,
        "potencia_tx": 20      # em dBm
    },
    {
        "endereco_rede": 3,
        "spreading_factor": 12,
        "bandwidth": 125,      # em kHz
        "coding_rate": 8,
        "potencia_tx": 20      # em dBm
    }
]

# Nome do arquivo de saída
ARQUIVO_CSV = "end_devices_net_par.csv"

# Ordens das colunas (cabeçalho)
campos = ["endereco_rede", "spreading_factor", "bandwidth", "coding_rate", "potencia_tx"]

# -------------------------------------------------------------------
# 2. Criação e Escrita no Arquivo CSV
# -------------------------------------------------------------------
with open(ARQUIVO_CSV, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=campos)
    
    # Escreve o cabeçalho e todas as linhas de uma só vez
    writer.writeheader()
    writer.writerows(end_devices)

print(f"Arquivo '{ARQUIVO_CSV}' criado e dados salvos com sucesso!")

# -------------------------------------------------------------------
# 3. Teste de Leitura Rápida do CSV Gerado
# -------------------------------------------------------------------
print("\n--- Conteúdo do arquivo CSV lido ---")
with open(ARQUIVO_CSV, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for linha in reader:
        print(f"Endereço: {linha['endereco_rede']} | SF: {linha['spreading_factor']} | "
              f"BW: {linha['bandwidth']} kHz | CR: {linha['coding_rate']} | Tx: {linha['potencia_tx']} dBm")
