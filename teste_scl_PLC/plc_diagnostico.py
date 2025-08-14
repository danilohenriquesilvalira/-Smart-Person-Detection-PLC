import snap7
import struct
import re
import os

# --- CONFIGURAÇÃO ---
PLC_IP = '192.168.0.33'
RACK = 0
SLOT = 1

SCL_FILE_PATH = r'C:\Users\Admin\Downloads\FC_IA_ECLUSA.scl'

# Configuração do DB20
DB_NUMBER = 20
DB_START_OFFSET = 0
# Aumentamos o tamanho da leitura para ter certeza de que não estamos cortando dados
# O timer começa no offset 2.0, então vamos ler até pelo menos o byte 5.
DB_SIZE = 5

# --- FUNÇÕES DE CONEXÃO E LEITURA ---
def conectar_plc(ip, rack, slot):
    print(f"Tentando conectar ao PLC em {ip}...")
    try:
        plc = snap7.client.Client()
        plc.connect(ip, rack, slot)
        if plc.get_connected():
            print("Conectado ao PLC com sucesso!")
            return plc
        else:
            print("Erro: Não foi possível conectar ao PLC. Verifique o IP e as configurações.")
            return None
    except Exception as e:
        print(f"Erro inesperado na conexão: {e}")
        return None

def ler_db_tags(plc, db_number, start, size):
    try:
        data = plc.db_read(db_number, start, size)
        
        # --- AQUI ESTÁ A NOVIDADE: IMPRIMIR OS DADOS BRUTOS ---
        print(f"\n--- Dados brutos do DB{db_number} lidos (tamanho {len(data)} bytes) ---")
        print(f"Array de bytes: {data}")
        print("-" * 50)
        
        if len(data) < 1:
            print("Erro: O PLC retornou um array de bytes vazio. Verifique o DB e os offsets.")
            return None

        # Mapeia os dados lidos para as tags do DB_IA_ECLUSA.
        tags = {
            'comando_ligar': snap7.util.get_bool(data, 0, 0),
            'comando_desligar': snap7.util.get_bool(data, 0, 1),
            'sensor_termico': snap7.util.get_bool(data, 0, 2),
            'feedback_motor_ligado': snap7.util.get_bool(data, 0, 3),
            'saida_motor': snap7.util.get_bool(data, 0, 4),
            'falha_sobrecarga': snap7.util.get_bool(data, 0, 5),
            'falha_motor_nao_liga': snap7.util.get_bool(data, 0, 6)
        }

        # Adiciona um log detalhado da leitura de cada bit
        print("--- Detalhe da leitura dos bits ---")
        byte_lido = data[0]
        for i in range(7):
            bit_estado = (byte_lido >> i) & 1
            print(f"Byte 0, Bit {i}: Estado = {bit_estado}")
        print("-" * 50)
        
        return tags
    except Exception as e:
        print(f"Erro ao ler o DB{db_number}: {e}")
        return None

# --- FUNÇÃO DE DIAGNÓSTICO (mantida da versão anterior) ---
def realizar_diagnostico(tags_plc):
    if tags_plc is None:
        print("Não foi possível realizar o diagnóstico. Dados do PLC não foram lidos.")
        return

    print("\n--- Relatório de Diagnóstico ---")

    if tags_plc['falha_sobrecarga']:
        print("DIAGNÓSTICO: Falha de SOBRECARGA está ATIVA.")
        print("Causa provável: O sensor térmico está em estado de sobrecarga.")
        if tags_plc['sensor_termico']:
            print("Ação: Verifique o sensor físico ou a fiação. O sensor térmico está ativado.")
        else:
            print("Ação: A falha está travada na lógica. Verifique o código PLC ou reinicie o sistema.")
        print("-" * 20)
    
    if tags_plc['falha_motor_nao_liga']:
        print("DIAGNÓSTICO: Falha de MOTOR NÃO LIGA está ATIVA.")
        print("Causa provável: O motor não ligou em tempo hábil após o comando.")
        if tags_plc['saida_motor'] and not tags_plc['feedback_motor_ligado']:
            print("Ação: O PLC está comandando a saída, mas não recebeu o feedback do motor. Verifique a contactora, fiação e o próprio motor.")
        else:
            print("Ação: Condição de falha não esperada. A falha pode ter sido gerada por outro motivo.")
        print("-" * 20)

    if not tags_plc['falha_sobrecarga'] and not tags_plc['falha_motor_nao_liga']:
        print("Nenhuma falha ativa foi detectada. O sistema está operando normalmente.")
        print("-" * 20)

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    plc = conectar_plc(PLC_IP, RACK, SLOT)
    
    if plc:
        tags_do_plc = ler_db_tags(plc, DB_NUMBER, DB_START_OFFSET, DB_SIZE)
        
        if tags_do_plc:
            print("\nValores Atuais do DB20 (DB_IA_ECLUSA):")
            for tag, valor in tags_do_plc.items():
                print(f"  - {tag}: {valor}")
            
            realizar_diagnostico(tags_do_plc)
        
        plc.disconnect()
        print("Desconectado do PLC.")