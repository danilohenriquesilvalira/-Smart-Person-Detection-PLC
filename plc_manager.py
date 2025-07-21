import snap7
import struct
import time

class PLCManager:
    def __init__(self, ip="192.168.0.33", rack=0, slot=1):
        self.plc = snap7.client.Client()
        self.ip = ip
        self.rack = rack
        self.slot = slot
        self.conectado = False
        self.db17_number = 17
        self.db18_number = 18
        self.db18_disponivel = False
        self.ultimo_envio = None
        
    def conectar(self):
        """Conectar ao PLC"""
        try:
            self.plc.connect(self.ip, self.rack, self.slot)
            test_data = self.plc.db_read(self.db17_number, 16, 1)
            self.conectado = True
            self._verificar_db18()
            if self.db18_disponivel:
                self._inicializar_db18()
            return True
        except Exception as e:
            print(f"❌ PLC Falhou: {e}")
            self.conectado = False
            return False
    
    def _verificar_db18(self):
        """Verificar se DB18 existe"""
        try:
            test_data = self.plc.db_read(self.db18_number, 0, 28)
            self.db18_disponivel = True
            return True
        except:
            self.db18_disponivel = False
            return False
    
    def _inicializar_db18(self):
        """Inicializar DB18 com valores padrão"""
        try:
            # Zerar comandos
            self.plc.db_write(self.db18_number, 0, bytearray([0]))
            # Sensibilidade padrão (0.1)
            sens_data = struct.pack('>f', 0.1)
            self.plc.db_write(self.db18_number, 2, sens_data)
            print("✅ DB18 inicializada")
        except Exception as e:
            print(f"❌ Erro inicializando DB18: {e}")
            self.db18_disponivel = False
    
    def ler_comandos(self):
        """Ler comandos do PLC"""
        if not self.conectado or not self.db18_disponivel:
            return {}
        
        try:
            # Ler comandos (byte 0)
            data = self.plc.db_read(self.db18_number, 0, 1)
            comandos_byte = data[0]
            
            # Ler sensibilidade (DBD2)
            sens_data = self.plc.db_read(self.db18_number, 2, 4)
            sensibilidade = struct.unpack('>f', sens_data)[0]
            
            # Extrair comandos
            comandos = {
                'treinar': bool(comandos_byte & 0x01),
                'detectar': bool(comandos_byte & 0x02),
                'reset': bool(comandos_byte & 0x04),
                'capturar_sem_copo': bool(comandos_byte & 0x08),
                'capturar_copo_bom': bool(comandos_byte & 0x10),
                'capturar_danificado': bool(comandos_byte & 0x20),
                'sensibilidade': sensibilidade if 0.01 <= sensibilidade <= 0.5 else 0.1
            }
            
            # Limpar comandos processados
            if comandos_byte > 0:
                self.plc.db_write(self.db18_number, 0, bytearray([0]))
            
            return comandos
            
        except Exception as e:
            print(f"❌ Erro lendo comandos: {e}")
            self.db18_disponivel = False
            return {}
    
    def enviar_valores(self, valor_sem_copo, valor_copo_bom, valor_danificado):
        """Enviar valores medidos para PLC"""
        if not self.conectado or not self.db18_disponivel:
            return False
        
        try:
            # Enviar valores (DBD6, DBD10, DBD14)
            dados = bytearray(12)
            dados[0:4] = struct.pack('>f', valor_sem_copo)
            dados[4:8] = struct.pack('>f', valor_copo_bom)
            dados[8:12] = struct.pack('>f', valor_danificado)
            self.plc.db_write(self.db18_number, 6, dados)
            return True
        except Exception as e:
            print(f"❌ Erro enviando valores: {e}")
            self.db18_disponivel = False
            return False
    
    def enviar_status(self, treinamento_completo, contador_sem, contador_bom, contador_dano, estado_atual):
        """Enviar status para PLC"""
        if not self.conectado or not self.db18_disponivel:
            return False
        
        try:
            # Status bits (DBX18.0-2)
            status_byte = 0
            if treinamento_completo:
                status_byte |= 0x01
            if self.conectado:
                status_byte |= 0x02
            if estado_atual == "COPO_DANIFICADO":
                status_byte |= 0x04
            
            self.plc.db_write(self.db18_number, 18, bytearray([status_byte]))
            
            # Contadores e estado (DBW20-26)
            dados = bytearray(8)
            dados[0:2] = struct.pack('>h', contador_sem)
            dados[2:4] = struct.pack('>h', contador_bom)
            dados[4:6] = struct.pack('>h', contador_dano)
            
            # Estado (0=Sem, 1=Bom, 2=Dano)
            estado_num = {"SEM_COPO": 0, "COPO_BOM": 1, "COPO_DANIFICADO": 2}.get(estado_atual, 0)
            dados[6:8] = struct.pack('>h', estado_num)
            
            self.plc.db_write(self.db18_number, 20, dados)
            return True
            
        except Exception as e:
            print(f"❌ Erro enviando status: {e}")
            self.db18_disponivel = False
            return False
    
    def enviar_db17_compatibilidade(self, estado):
        """Enviar para DB17 (compatibilidade)"""
        if not self.conectado or estado == self.ultimo_envio:
            return
        
        try:
            data = self.plc.db_read(self.db17_number, 16, 1)
            
            if estado == "COPO_DANIFICADO":
                data[0] = data[0] | 0x02
                self.plc.db_write(self.db17_number, 16, data)
                # Timestamp
                timestamp = int(time.time())
                data_timestamp = struct.pack('>L', timestamp)
                self.plc.db_write(self.db17_number, 18, data_timestamp)
            else:
                data[0] = data[0] & 0xFD
                self.plc.db_write(self.db17_number, 16, data)
            
            self.ultimo_envio = estado
            
        except:
            pass
    
    def desconectar(self):
        """Desconectar do PLC"""
        if self.conectado:
            try:
                # Limpar DB17
                data = self.plc.db_read(self.db17_number, 16, 1)
                data[0] = data[0] & 0xFD
                self.plc.db_write(self.db17_number, 16, data)
                
                # Limpar DB18
                if self.db18_disponivel:
                    self.plc.db_write(self.db18_number, 0, bytearray([0]))
                
                self.plc.disconnect()
            except:
                pass
            self.conectado = False