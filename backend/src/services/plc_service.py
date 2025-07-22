"""
🔧 Serviço PLC - Smart Detection Backend
"""
import snap7
import struct
import time
from typing import Dict, Optional

from config.settings import PLC_CONFIG

class PLCService:
    """🔌 Serviço de comunicação com PLC"""
    
    def __init__(self):
        self.plc = snap7.client.Client()
        self.ip = PLC_CONFIG["ip"]
        self.rack = PLC_CONFIG["rack"]
        self.slot = PLC_CONFIG["slot"]
        self.timeout = PLC_CONFIG["timeout"]
        
        # Configuração dos DBs
        self.db17_number = PLC_CONFIG["db17_number"]
        self.db18_number = PLC_CONFIG["db18_number"]
        
        # Status de conexão
        self.conectado = False
        self.db18_disponivel = False
        self.ultimo_envio = None
        
        print(f"🔌 Serviço PLC inicializado: {self.ip}:{self.rack}.{self.slot}")
    
    def connect(self) -> bool:
        """🔗 Conectar ao PLC"""
        try:
            print(f"🔌 Conectando ao PLC {self.ip}...")
            
            # Conectar ao PLC
            self.plc.connect(self.ip, self.rack, self.slot)
            
            # Testar comunicação com DB17
            test_data = self.plc.db_read(self.db17_number, 16, 1)
            
            self.conectado = True
            print("✅ PLC conectado com sucesso")
            
            # Verificar e configurar DB18
            self._setup_db18()
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao conectar PLC: {e}")
            self.conectado = False
            self.db18_disponivel = False
            return False
    
    def disconnect(self):
        """🔌 Desconectar do PLC"""
        if not self.conectado:
            return
        
        try:
            # Limpar dados antes de desconectar
            self._clear_plc_data()
            
            # Desconectar
            self.plc.disconnect()
            
            self.conectado = False
            self.db18_disponivel = False
            
            print("🔌 PLC desconectado")
            
        except Exception as e:
            print(f"⚠️ Erro ao desconectar PLC: {e}")
        
        finally:
            self.conectado = False
            self.db18_disponivel = False
    
    def _setup_db18(self):
        """⚙️ Configurar DB18"""
        try:
            # Testar acesso ao DB18
            test_data = self.plc.db_read(self.db18_number, 0, 28)
            self.db18_disponivel = True
            
            print("✅ DB18 disponível")
            
            # Inicializar DB18 com valores padrão
            self._initialize_db18()
            
        except Exception as e:
            print(f"⚠️ DB18 não disponível: {e}")
            self.db18_disponivel = False
    
    def _initialize_db18(self):
        """🏗️ Inicializar DB18 com valores padrão"""
        try:
            # Zerar comandos (DBB0)
            self.plc.db_write(self.db18_number, 0, bytearray([0]))
            
            # Sensibilidade padrão 0.1 (DBD2)
            sens_data = struct.pack('>f', 0.1)
            self.plc.db_write(self.db18_number, 2, sens_data)
            
            print("🏗️ DB18 inicializada com valores padrão")
            
        except Exception as e:
            print(f"❌ Erro inicializando DB18: {e}")
            self.db18_disponivel = False
    
    def _clear_plc_data(self):
        """🧹 Limpar dados do PLC"""
        try:
            # Limpar DB17
            if self.conectado:
                data = self.plc.db_read(self.db17_number, 16, 1)
                data[0] = data[0] & 0xFD  # Limpar bit de copo danificado
                self.plc.db_write(self.db17_number, 16, data)
            
            # Limpar DB18
            if self.db18_disponivel:
                self.plc.db_write(self.db18_number, 0, bytearray([0]))
            
            print("🧹 Dados do PLC limpos")
            
        except Exception as e:
            print(f"⚠️ Erro limpando dados PLC: {e}")
    
    def ler_comandos(self) -> Dict:
        """📥 Ler comandos do PLC"""
        if not self.conectado or not self.db18_disponivel:
            return {}
        
        try:
            # Ler comandos (DBB0)
            data = self.plc.db_read(self.db18_number, 0, 1)
            comandos_byte = data[0]
            
            # Ler sensibilidade (DBD2)
            sens_data = self.plc.db_read(self.db18_number, 2, 4)
            sensibilidade = struct.unpack('>f', sens_data)[0]
            
            # Validar sensibilidade
            if not (0.01 <= sensibilidade <= 0.5):
                sensibilidade = 0.1
            
            # Extrair comandos individuais
            comandos = {
                'treinar': bool(comandos_byte & 0x01),
                'detectar': bool(comandos_byte & 0x02),
                'reset': bool(comandos_byte & 0x04),
                'capturar_sem_copo': bool(comandos_byte & 0x08),
                'capturar_copo_bom': bool(comandos_byte & 0x10),
                'capturar_danificado': bool(comandos_byte & 0x20),
                'sensibilidade': sensibilidade
            }
            
            # Limpar comandos após leitura
            if comandos_byte > 0:
                self.plc.db_write(self.db18_number, 0, bytearray([0]))
                print(f"📥 Comandos PLC processados: {[k for k, v in comandos.items() if v and k != 'sensibilidade']}")
            
            return comandos
            
        except Exception as e:
            print(f"❌ Erro lendo comandos PLC: {e}")
            self.db18_disponivel = False
            return {}
    
    def enviar_valores(self, valor_sem_copo: float, valor_copo_bom: float, valor_danificado: float) -> bool:
        """📤 Enviar valores de detecção para o PLC"""
        if not self.conectado or not self.db18_disponivel:
            return False
        
        try:
            # Preparar dados (DBD6, DBD10, DBD14)
            dados = bytearray(12)
            dados[0:4] = struct.pack('>f', valor_sem_copo)
            dados[4:8] = struct.pack('>f', valor_copo_bom)
            dados[8:12] = struct.pack('>f', valor_danificado)
            
            # Enviar para PLC
            self.plc.db_write(self.db18_number, 6, dados)
            
            return True
            
        except Exception as e:
            print(f"❌ Erro enviando valores para PLC: {e}")
            self.db18_disponivel = False
            return False
    
    def enviar_status(self, treinamento_completo: bool, contador_sem: int, 
                     contador_bom: int, contador_dano: int, estado_atual: str) -> bool:
        """📤 Enviar status do sistema para o PLC"""
        if not self.conectado or not self.db18_disponivel:
            return False
        
        try:
            # Status bits (DBX18.0-2)
            status_byte = 0
            
            if treinamento_completo:
                status_byte |= 0x01  # Bit 0: Treinamento completo
            
            if self.conectado:
                status_byte |= 0x02  # Bit 1: Sistema conectado
            
            if estado_atual == "COPO_DANIFICADO":
                status_byte |= 0x04  # Bit 2: Copo danificado detectado
            
            # Enviar status
            self.plc.db_write(self.db18_number, 18, bytearray([status_byte]))
            
            # Contadores e estado (DBW20-26)
            dados = bytearray(8)
            dados[0:2] = struct.pack('>h', contador_sem)      # DBW20
            dados[2:4] = struct.pack('>h', contador_bom)      # DBW22
            dados[4:6] = struct.pack('>h', contador_dano)     # DBW24
            
            # Estado atual como número (DBW26)
            estado_map = {"SEM_COPO": 0, "COPO_BOM": 1, "COPO_DANIFICADO": 2}
            estado_num = estado_map.get(estado_atual, 0)
            dados[6:8] = struct.pack('>h', estado_num)
            
            # Enviar contadores
            self.plc.db_write(self.db18_number, 20, dados)
            
            return True
            
        except Exception as e:
            print(f"❌ Erro enviando status para PLC: {e}")
            self.db18_disponivel = False
            return False
    
    def enviar_db17_compatibilidade(self, estado: str):
        """📤 Enviar para DB17 (compatibilidade com sistema antigo)"""
        if not self.conectado or estado == self.ultimo_envio:
            return
        
        try:
            # Ler estado atual do DB17
            data = self.plc.db_read(self.db17_number, 16, 1)
            
            if estado == "COPO_DANIFICADO":
                # Ativar bit de copo danificado
                data[0] = data[0] | 0x02
                
                # Timestamp
                timestamp = int(time.time())
                data_timestamp = struct.pack('>L', timestamp)
                self.plc.db_write(self.db17_number, 18, data_timestamp)
                
                print("🚨 Sinal de copo danificado enviado para DB17")
                
            else:
                # Limpar bit de copo danificado
                data[0] = data[0] & 0xFD
            
            # Enviar dados atualizados
            self.plc.db_write(self.db17_number, 16, data)
            
            self.ultimo_envio = estado
            
        except Exception as e:
            print(f"⚠️ Erro enviando para DB17: {e}")
    
    def get_status(self) -> Dict:
        """📊 Obter status do PLC"""
        return {
            "connected": self.conectado,
            "db18_available": self.db18_disponivel,
            "ip": self.ip,
            "rack": self.rack,
            "slot": self.slot,
            "db17_number": self.db17_number,
            "db18_number": self.db18_number,
            "last_command_sent": self.ultimo_envio
        }
    
    def test_connection(self) -> bool:
        """🧪 Testar conexão com PLC"""
        if not self.conectado:
            return False
        
        try:
            # Teste simples de leitura
            test_data = self.plc.db_read(self.db17_number, 16, 1)
            return True
        except:
            return False
    
    def reconnect(self) -> bool:
        """🔄 Reconectar ao PLC"""
        print("🔄 Tentando reconectar ao PLC...")
        
        # Desconectar se conectado
        if self.conectado:
            self.disconnect()
        
        # Aguardar um pouco
        time.sleep(1)
        
        # Tentar conectar novamente
        return self.connect()
    
    def __del__(self):
        """🧹 Limpeza na destruição"""
        self.disconnect()

# 🏭 Instância global do serviço PLC
plc_service = PLCService()