import cv2
import time
import numpy as np
import snap7
import struct
import os

class DetectorSimplesPlc:
    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.cap = None
        
        # DADOS DE TREINAMENTO
        self.fotos_sem_copo = []     
        self.fotos_copo_bom = []     
        self.fotos_copo_danificado = []  
        self.pasta_dados = "dados_copo"
        
        # ÁREA
        self.area_coords = None
        self.tamanho_area = 200
        
        # CONTADORES
        self.contador_sem_copo = 0
        self.contador_copo_bom = 0
        self.contador_copo_danificado = 0
        self.max_fotos = 10
        
        # ESTADO ATUAL
        self.modo_atual = "AGUARDANDO"
        self.estado_detectado = "SEM_COPO"
        self.treinamento_completo = False
        self.ultima_captura = 0
        
        # VALORES REAIS QUE VOCÊ VÊ
        self.valor_sem_copo = 0.0      
        self.valor_copo_bom = 0.0      
        self.valor_copo_danificado = 0.0  
        
        # SENSIBILIDADE (vem do PLC)
        self.sensibilidade = 0.1   # Padrão
        
        # PLC SIMPLIFICADO
        self.plc = snap7.client.Client()
        self.plc_ip = "192.168.0.33"
        self.plc_rack = 0
        self.plc_slot = 1
        self.db17_number = 17  # Original para compatibilidade
        self.db18_number = 18  # Nova interface simples
        self.plc_conectado = False
        self.db18_disponivel = False
        self.ultimo_envio = None
        
        # HISTÓRICO PARA ESTABILIDADE
        self.historico = []
        
        # CONECTAR TUDO
        self.conectar_plc()
        self.criar_pastas()
        self.carregar_fotos()
        self.inicializar_db18()
        
    """
    ==========================================
    ESTRUTURA DB18 SIMPLES (28 bytes)
    ==========================================
    
    COMANDOS (PLC → Sistema):
    ------------------------
    DB18.DBX0.0 = BOOL - Iniciar Treinamento
    DB18.DBX0.1 = BOOL - Iniciar Detecção  
    DB18.DBX0.2 = BOOL - Reset Sistema
    DB18.DBX0.3 = BOOL - Capturar Sem Copo
    DB18.DBX0.4 = BOOL - Capturar Copo Bom
    DB18.DBX0.5 = BOOL - Capturar Danificado
    
    PARÂMETRO (PLC → Sistema):
    -------------------------
    DB18.DBD2 = REAL - Sensibilidade (0.01-0.5)
    
    VALORES (Sistema → PLC):
    -----------------------
    DB18.DBD6  = REAL - Valor Sem Copo Medido
    DB18.DBD10 = REAL - Valor Copo Bom Medido
    DB18.DBD14 = REAL - Valor Danificado Medido
    
    STATUS (Sistema → PLC):
    ----------------------
    DB18.DBX18.0 = BOOL - Treinamento Completo
    DB18.DBX18.1 = BOOL - Sistema Conectado
    DB18.DBX18.2 = BOOL - Copo Danificado Detectado
    
    CONTADORES (Sistema → PLC):
    --------------------------
    DB18.DBW20 = INT - Contador Sem Copo (0-10)
    DB18.DBW22 = INT - Contador Copo Bom (0-10)
    DB18.DBW24 = INT - Contador Danificado (0-10)
    DB18.DBW26 = INT - Estado Atual (0=Sem, 1=Bom, 2=Dano)
    """
    
    def criar_pastas(self):
        """Criar pastas para os 3 estados"""
        pastas = [
            self.pasta_dados,
            os.path.join(self.pasta_dados, "sem_copo"),
            os.path.join(self.pasta_dados, "copo_bom"),
            os.path.join(self.pasta_dados, "copo_danificado")
        ]
        for pasta in pastas:
            if not os.path.exists(pasta):
                os.makedirs(pasta)
    
    def carregar_fotos(self):
        """Carregar fotos dos 3 estados"""
        estados = [
            ("sem_copo", self.fotos_sem_copo),
            ("copo_bom", self.fotos_copo_bom), 
            ("copo_danificado", self.fotos_copo_danificado)
        ]
        
        for pasta_nome, lista_fotos in estados:
            pasta_path = os.path.join(self.pasta_dados, pasta_nome)
            if os.path.exists(pasta_path):
                for arquivo in sorted(os.listdir(pasta_path)):
                    if arquivo.endswith('.jpg'):
                        img = cv2.imread(os.path.join(pasta_path, arquivo), cv2.IMREAD_GRAYSCALE)
                        if img is not None:
                            img = cv2.resize(img, (100, 100))
                            lista_fotos.append(img)
        
        # Atualizar contadores
        self.contador_sem_copo = len(self.fotos_sem_copo)
        self.contador_copo_bom = len(self.fotos_copo_bom)
        self.contador_copo_danificado = len(self.fotos_copo_danificado)
        
        # Verificar se completo
        if (self.contador_sem_copo >= self.max_fotos and 
            self.contador_copo_bom >= self.max_fotos and
            self.contador_copo_danificado >= self.max_fotos):
            self.treinamento_completo = True
    
    def conectar_plc(self):
        """Conectar PLC"""
        print("🔌 Conectando PLC...")
        try:
            self.plc.connect(self.plc_ip, self.plc_rack, self.plc_slot)
            test_data = self.plc.db_read(self.db17_number, 16, 1)
            self.plc_conectado = True
            print("✅ PLC Conectado")
            return True
        except Exception as e:
            print(f"❌ PLC Falhou: {e}")
            self.plc_conectado = False
            return False
    
    def verificar_db18(self):
        """Verificar se DB18 existe"""
        if not self.plc_conectado:
            return False
        try:
            # Tentar ler 28 bytes
            test_data = self.plc.db_read(self.db18_number, 0, 28)
            return True
        except Exception as e:
            print(f"⚠️ DB18 não disponível: {e}")
            print("💡 Crie DB18 com 28 bytes no PLC")
            return False
    
    def inicializar_db18(self):
        """Inicializar DB18 com valores padrão"""
        if not self.plc_conectado:
            return
            
        if not self.verificar_db18():
            print("❌ DB18 não encontrada")
            return
            
        try:
            # Zerar comandos
            self.plc.db_write(self.db18_number, 0, bytearray([0]))
            
            # Sensibilidade padrão (0.1)
            sens_data = struct.pack('>f', 0.1)
            self.plc.db_write(self.db18_number, 2, sens_data)
            
            print("✅ DB18 inicializada")
            self.db18_disponivel = True
            
        except Exception as e:
            print(f"❌ Erro inicializando DB18: {e}")
            self.db18_disponivel = False
    
    def ler_comandos_plc(self):
        """Ler comandos do PLC"""
        if not self.plc_conectado or not self.db18_disponivel:
            return
        
        try:
            # Ler comandos (byte 0)
            data = self.plc.db_read(self.db18_number, 0, 1)
            comandos = data[0]
            
            # Ler sensibilidade (DBD2)
            sens_data = self.plc.db_read(self.db18_number, 2, 4)
            nova_sensibilidade = struct.unpack('>f', sens_data)[0]
            
            # Validar e aplicar sensibilidade
            if 0.01 <= nova_sensibilidade <= 0.5:
                if abs(nova_sensibilidade - self.sensibilidade) > 0.001:
                    self.sensibilidade = nova_sensibilidade
                    print(f"📡 PLC: Nova sensibilidade {self.sensibilidade:.3f}")
            
            # Processar comandos
            comandos_executados = 0
            
            if comandos & 0x01:  # Treinar
                self.modo_atual = "TREINAMENTO"
                print("📚 PLC: Comando TREINAR")
                comandos_executados |= 0x01
                
            if comandos & 0x02:  # Detectar
                if self.treinamento_completo:
                    self.modo_atual = "DETECCAO"
                    print("🎯 PLC: Comando DETECTAR")
                comandos_executados |= 0x02
                    
            if comandos & 0x04:  # Reset
                self.reset_sistema()
                print("🔄 PLC: Comando RESET")
                comandos_executados |= 0x04
                
            if comandos & 0x08:  # Capturar Sem Copo
                if self.modo_atual == "TREINAMENTO":
                    self.processar_captura("sem_copo")
                comandos_executados |= 0x08
                    
            if comandos & 0x10:  # Capturar Copo Bom
                if self.modo_atual == "TREINAMENTO":
                    self.processar_captura("copo_bom")
                comandos_executados |= 0x10
                    
            if comandos & 0x20:  # Capturar Danificado
                if self.modo_atual == "TREINAMENTO":
                    self.processar_captura("copo_danificado")
                comandos_executados |= 0x20
            
            # Limpar comandos executados
            if comandos_executados > 0:
                novo_comando = comandos & ~comandos_executados
                self.plc.db_write(self.db18_number, 0, bytearray([novo_comando]))
            
        except Exception as e:
            print(f"❌ Erro lendo comandos PLC: {e}")
            self.db18_disponivel = False
    
    def enviar_valores_plc(self):
        """Enviar valores medidos para PLC"""
        if not self.plc_conectado or not self.db18_disponivel:
            return
        
        try:
            # Enviar valores (DBD6, DBD10, DBD14)
            dados = bytearray(12)
            dados[0:4] = struct.pack('>f', self.valor_sem_copo)
            dados[4:8] = struct.pack('>f', self.valor_copo_bom)
            dados[8:12] = struct.pack('>f', self.valor_copo_danificado)
            
            self.plc.db_write(self.db18_number, 6, dados)
            
        except Exception as e:
            print(f"❌ Erro enviando valores: {e}")
            self.db18_disponivel = False
    
    def enviar_status_plc(self):
        """Enviar status para PLC"""
        if not self.plc_conectado or not self.db18_disponivel:
            return
        
        try:
            # Status bits (DBX18.0-2)
            status_byte = 0
            if self.treinamento_completo:
                status_byte |= 0x01
            if self.plc_conectado:
                status_byte |= 0x02
            if self.estado_detectado == "COPO_DANIFICADO":
                status_byte |= 0x04
            
            self.plc.db_write(self.db18_number, 18, bytearray([status_byte]))
            
            # Contadores (DBW20-26)
            dados = bytearray(8)
            dados[0:2] = struct.pack('>h', self.contador_sem_copo)
            dados[2:4] = struct.pack('>h', self.contador_copo_bom)
            dados[4:6] = struct.pack('>h', self.contador_copo_danificado)
            
            # Estado atual
            if self.estado_detectado == "SEM_COPO":
                estado = 0
            elif self.estado_detectado == "COPO_BOM":
                estado = 1
            else:
                estado = 2
            dados[6:8] = struct.pack('>h', estado)
            
            self.plc.db_write(self.db18_number, 20, dados)
            
        except Exception as e:
            print(f"❌ Erro enviando status: {e}")
            self.db18_disponivel = False
    
    def processar_captura(self, categoria):
        """Processar comando de captura do PLC"""
        if not hasattr(self, 'frame_atual') or self.frame_atual is None:
            return
            
        agora = time.time()
        if agora - self.ultima_captura < 1.0:
            return
            
        sucesso = self.salvar_foto(self.frame_atual, categoria)
        if sucesso:
            print(f"📸 PLC: Capturou {categoria}")
    
    def medir_valores(self, frame):
        """MEDIR VALORES REAIS"""
        if not self.treinamento_completo:
            return
        
        # EXTRAIR ÁREA
        x1, y1, x2, y2 = self.area_coords
        area = frame[y1:y2, x1:x2]
        if len(area.shape) == 3:
            area = cv2.cvtColor(area, cv2.COLOR_BGR2GRAY)
        area = cv2.resize(area, (100, 100))
        
        # MEDIR SIMILARIDADE COM CADA ESTADO
        self.valor_sem_copo = self.calcular_similaridade(area, self.fotos_sem_copo)
        self.valor_copo_bom = self.calcular_similaridade(area, self.fotos_copo_bom)
        self.valor_copo_danificado = self.calcular_similaridade(area, self.fotos_copo_danificado)
    
    def calcular_similaridade(self, area_atual, fotos_estado):
        """Calcular similaridade"""
        if not fotos_estado:
            return 0.0
        
        similarities = []
        for foto in fotos_estado:
            resultado = cv2.matchTemplate(area_atual, foto, cv2.TM_CCOEFF_NORMED)
            _, similarity, _, _ = cv2.minMaxLoc(resultado)
            similarities.append(similarity)
        
        similarities.sort(reverse=True)
        top_similarities = similarities[:3] if len(similarities) >= 3 else similarities
        return np.mean(top_similarities)
    
    def decidir_estado(self):
        """DECISÃO SIMPLES"""
        if not self.treinamento_completo:
            return None
        
        # Encontrar o maior valor
        valores = {
            "SEM_COPO": self.valor_sem_copo,
            "COPO_BOM": self.valor_copo_bom,
            "COPO_DANIFICADO": self.valor_copo_danificado
        }
        
        ordenados = sorted(valores.items(), key=lambda x: x[1], reverse=True)
        primeiro_estado, primeiro_valor = ordenados[0]
        segundo_estado, segundo_valor = ordenados[1]
        
        diferenca = primeiro_valor - segundo_valor
        
        if diferenca >= self.sensibilidade:
            return primeiro_estado
        else:
            return None
    
    def analisar_estabilidade(self, deteccao_atual):
        """Estabilidade simples"""
        if deteccao_atual is None:
            return self.estado_detectado
        
        self.historico.append(deteccao_atual)
        if len(self.historico) > 3:
            self.historico.pop(0)
        
        if len(self.historico) >= 2:
            from collections import Counter
            contador = Counter(self.historico)
            mais_comum, ocorrencias = contador.most_common(1)[0]
            
            if ocorrencias >= 2:
                return mais_comum
        
        return self.estado_detectado
    
    def salvar_foto(self, frame, categoria):
        """Salvar foto"""
        x1, y1, x2, y2 = self.area_coords
        area = frame[y1:y2, x1:x2]
        if len(area.shape) == 3:
            area = cv2.cvtColor(area, cv2.COLOR_BGR2GRAY)
        area = cv2.resize(area, (100, 100))
        
        # Incrementar contador
        if categoria == "sem_copo":
            if self.contador_sem_copo >= self.max_fotos:
                return False
            self.contador_sem_copo += 1
            contador = self.contador_sem_copo
            self.fotos_sem_copo.append(area)
        elif categoria == "copo_bom":
            if self.contador_copo_bom >= self.max_fotos:
                return False
            self.contador_copo_bom += 1
            contador = self.contador_copo_bom
            self.fotos_copo_bom.append(area)
        else:
            if self.contador_copo_danificado >= self.max_fotos:
                return False
            self.contador_copo_danificado += 1
            contador = self.contador_copo_danificado
            self.fotos_copo_danificado.append(area)
        
        nome = f"{categoria}_{contador:02d}.jpg"
        pasta = os.path.join(self.pasta_dados, categoria)
        cv2.imwrite(os.path.join(pasta, nome), area)
        
        # Verificar se completo
        if (self.contador_sem_copo >= self.max_fotos and 
            self.contador_copo_bom >= self.max_fotos and
            self.contador_copo_danificado >= self.max_fotos):
            self.treinamento_completo = True
            print("🎉 TREINAMENTO COMPLETO!")
        
        self.ultima_captura = time.time()
        return True
    
    def reset_sistema(self):
        """Reset sistema"""
        self.contador_sem_copo = 0
        self.contador_copo_bom = 0
        self.contador_copo_danificado = 0
        self.fotos_sem_copo = []
        self.fotos_copo_bom = []
        self.fotos_copo_danificado = []
        self.treinamento_completo = False
        self.modo_atual = "AGUARDANDO"
        self.historico = []
        
        # Limpar arquivos
        import shutil
        for pasta in ["sem_copo", "copo_bom", "copo_danificado"]:
            pasta_path = os.path.join(self.pasta_dados, pasta)
            if os.path.exists(pasta_path):
                shutil.rmtree(pasta_path)
                os.makedirs(pasta_path)
    
    def enviar_db17(self, estado):
        """Enviar para DB17 original"""
        if not self.plc_conectado or estado == self.ultimo_envio:
            return
        
        try:
            data = self.plc.db_read(self.db17_number, 16, 1)
            
            if estado == "COPO_DANIFICADO":
                data[0] = data[0] | 0x02
                self.plc.db_write(self.db17_number, 16, data)
                
                timestamp = int(time.time())
                data_timestamp = struct.pack('>L', timestamp)
                self.plc.db_write(self.db17_number, 18, data_timestamp)
            else:
                data[0] = data[0] & 0xFD
                self.plc.db_write(self.db17_number, 16, data)
            
            self.ultimo_envio = estado
            
        except:
            pass
    
    def conectar_camera(self):
        """Conectar câmera"""
        self.cap = cv2.VideoCapture(self.rtsp_url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return self.cap.isOpened()
    
    def definir_area(self, frame):
        """Área central"""
        h, w = frame.shape[:2]
        centro_x, centro_y = w // 2, h // 2
        meio = self.tamanho_area // 2
        self.area_coords = (centro_x - meio, centro_y - meio, centro_x + meio, centro_y + meio)
    
    def desenhar_barra(self, frame, x, y, largura, altura, valor, cor, label):
        """Desenhar barra de valor"""
        # Fundo da barra
        cv2.rectangle(frame, (x, y), (x + largura, y + altura), (50, 50, 50), -1)
        
        # Valor da barra
        barra_largura = int(largura * min(valor, 1.0))
        if barra_largura > 0:
            cv2.rectangle(frame, (x, y), (x + barra_largura, y + altura), cor, -1)
        
        # Texto do valor
        texto = f"{label}: {valor:.3f}"
        cv2.putText(frame, texto, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)
        
        # Borda
        cv2.rectangle(frame, (x, y), (x + largura, y + altura), (255, 255, 255), 2)
    
    def desenhar_interface_simples(self, frame):
        """INTERFACE SIMPLES + PLC"""
        
        # PAINEL LATERAL DIREITO
        painel_x = frame.shape[1] - 400
        painel_y = 50
        painel_w = 380
        painel_h = 550
        
        # Fundo do painel
        overlay = frame.copy()
        cv2.rectangle(overlay, (painel_x, painel_y), (painel_x + painel_w, painel_y + painel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Borda do painel
        cv2.rectangle(frame, (painel_x, painel_y), (painel_x + painel_w, painel_y + painel_h), (255, 255, 255), 3)
        
        # TÍTULO
        cv2.putText(frame, "DETECTOR + PLC", (painel_x + 20, painel_y + 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        y_pos = painel_y + 80
        
        # STATUS PRINCIPAL
        if self.modo_atual == "AGUARDANDO":
            status = "AGUARDANDO PLC"
            cor_status = (255, 255, 0)
        elif self.modo_atual == "TREINAMENTO":
            status = "TREINAMENTO"
            cor_status = (0, 255, 255)
        else:
            if self.estado_detectado == "SEM_COPO":
                status = "SEM COPO"
                cor_status = (128, 128, 128)
            elif self.estado_detectado == "COPO_BOM":
                status = "COPO BOM"
                cor_status = (0, 255, 0)
            else:
                status = "COPO DANIFICADO"
                cor_status = (0, 0, 255)
        
        cv2.putText(frame, f"STATUS: {status}", (painel_x + 20, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor_status, 2)
        y_pos += 60
        
        # SENSIBILIDADE DO PLC
        cv2.putText(frame, f"SENSIBILIDADE PLC: {self.sensibilidade:.3f}", (painel_x + 20, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        y_pos += 40
        
        # VALORES MEDIDOS
        if self.treinamento_completo:
            cv2.putText(frame, "VALORES MEDIDOS:", (painel_x + 20, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_pos += 40
            
            # Barras de valores
            barra_w = 300
            barra_h = 30
            
            # SEM COPO
            self.desenhar_barra(frame, painel_x + 20, y_pos, barra_w, barra_h, 
                              self.valor_sem_copo, (128, 128, 128), "SEM COPO")
            y_pos += 60
            
            # COPO BOM
            self.desenhar_barra(frame, painel_x + 20, y_pos, barra_w, barra_h, 
                              self.valor_copo_bom, (0, 255, 0), "COPO BOM")
            y_pos += 60
            
            # COPO DANIFICADO
            self.desenhar_barra(frame, painel_x + 20, y_pos, barra_w, barra_h, 
                              self.valor_copo_danificado, (0, 0, 255), "DANIFICADO")
            y_pos += 80
            
            # DECISÃO
            cv2.putText(frame, "DECISAO:", (painel_x + 20, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_pos += 30
            
            # Mostrar decisão
            valores = [
                ("SEM COPO", self.valor_sem_copo, (128, 128, 128)),
                ("COPO BOM", self.valor_copo_bom, (0, 255, 0)),
                ("DANIFICADO", self.valor_copo_danificado, (0, 0, 255))
            ]
            
            valores.sort(key=lambda x: x[1], reverse=True)
            maior_nome, maior_valor, maior_cor = valores[0]
            segundo_nome, segundo_valor, _ = valores[1]
            
            diferenca = maior_valor - segundo_valor
            
            cv2.putText(frame, f"MAIOR: {maior_nome}", (painel_x + 20, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, maior_cor, 2)
            y_pos += 25
            
            cv2.putText(frame, f"DIFERENCA: {diferenca:.3f}", (painel_x + 20, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_pos += 25
            
            if diferenca >= self.sensibilidade:
                cv2.putText(frame, "DECISAO: ACEITA", (painel_x + 20, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "DECISAO: INCERTA", (painel_x + 20, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
        
        # CONTADORES DE TREINAMENTO
        y_pos = painel_y + painel_h - 150
        cv2.putText(frame, "TREINAMENTO:", (painel_x + 20, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_pos += 25
        cv2.putText(frame, f"Sem Copo: {self.contador_sem_copo}/10", (painel_x + 20, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1)
        y_pos += 20
        cv2.putText(frame, f"Copo Bom: {self.contador_copo_bom}/10", (painel_x + 20, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        y_pos += 20
        cv2.putText(frame, f"Danificado: {self.contador_copo_danificado}/10", (painel_x + 20, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        
        # PLC STATUS
        y_pos += 30
        if self.plc_conectado and self.db18_disponivel:
            plc_status = "PLC DB18: OK"
            plc_cor = (0, 255, 0)
        elif self.plc_conectado:
            plc_status = "PLC: OK | DB18: OFF"
            plc_cor = (255, 255, 0)
        else:
            plc_status = "PLC: DESCONECTADO"
            plc_cor = (0, 0, 255)
        
        cv2.putText(frame, plc_status, (painel_x + 20, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, plc_cor, 1)
        
        # CONTROLES
        controles = [
            "CONTROLE VIA PLC DB18:",
            "- Treinar/Detectar/Reset",
            "- Capturar fotos",
            "- Ajustar sensibilidade",
            "",
            "TECLADO (backup):",
            "T=Treinar D=Detectar R=Reset",
            "V=SemCopo C=CopoBom S=Dano",
            "ESC=Sair"
        ]
        
        for i, controle in enumerate(controles):
            cv2.putText(frame, controle, (10, frame.shape[0] - (len(controles) - i) * 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
    
    def desenhar_area(self, frame):
        """Desenhar área de detecção"""
        if self.area_coords is None:
            return
        
        x1, y1, x2, y2 = self.area_coords
        
        if self.modo_atual == "DETECCAO":
            if self.estado_detectado == "SEM_COPO":
                cor = (128, 128, 128)
            elif self.estado_detectado == "COPO_BOM":
                cor = (0, 255, 0)
            else:
                cor = (0, 0, 255)
        else:
            cor = (255, 100, 0)
        
        cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 3)
        
        centro_x, centro_y = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.line(frame, (centro_x - 20, centro_y), (centro_x + 20, centro_y), cor, 2)
        cv2.line(frame, (centro_x, centro_y - 20), (centro_x, centro_y + 20), cor, 2)
    
    def executar(self):
        """EXECUTAR SISTEMA COM PLC"""
        print("🥤 DETECTOR SIMPLES + PLC")
        print("📊 Interface visual + Controle PLC simplificado")
        print("-" * 50)
        
        ret, frame = self.cap.read()
        if ret:
            self.definir_area(frame)
        
        contador_ciclos = 0
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            # Guardar frame para capturas via PLC
            self.frame_atual = frame
            
            # COMUNICAÇÃO PLC (a cada 100ms)
            if contador_ciclos % 3 == 0:
                if self.plc_conectado and self.db18_disponivel:
                    self.ler_comandos_plc()
                    if self.treinamento_completo:
                        self.enviar_valores_plc()
                    self.enviar_status_plc()
            
            # MEDIR VALORES E DETECTAR
            if self.treinamento_completo:
                self.medir_valores(frame)
                
                if self.modo_atual == "DETECCAO":
                    deteccao_atual = self.decidir_estado()
                    estado_estavel = self.analisar_estabilidade(deteccao_atual)
                    
                    if estado_estavel != self.estado_detectado:
                        self.estado_detectado = estado_estavel
                        self.enviar_db17(estado_estavel)
            
            self.desenhar_interface_simples(frame)
            self.desenhar_area(frame)
            
            cv2.imshow('DETECTOR SIMPLES + PLC', frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27:  # ESC
                break
            # Controles de backup via teclado
            elif key == ord('t'):
                self.modo_atual = "TREINAMENTO"
            elif key == ord('d'):
                if self.treinamento_completo:
                    self.modo_atual = "DETECCAO"
            elif key == ord('v') and self.modo_atual == "TREINAMENTO":
                if self.contador_sem_copo < self.max_fotos:
                    self.salvar_foto(frame, "sem_copo")
            elif key == ord('c') and self.modo_atual == "TREINAMENTO":
                if self.contador_copo_bom < self.max_fotos:
                    self.salvar_foto(frame, "copo_bom")
            elif key == ord('s') and self.modo_atual == "TREINAMENTO":
                if self.contador_copo_danificado < self.max_fotos:
                    self.salvar_foto(frame, "copo_danificado")
            elif key == ord('r'):
                self.reset_sistema()
            
            contador_ciclos += 1
        
        # CLEANUP
        if self.plc_conectado:
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
        
        self.cap.release()
        cv2.destroyAllWindows()

def main():
    print("🥤 DETECTOR SIMPLES + PLC SIMPLIFICADO")
    print("🎯 Interface visual + DB18 simples (28 bytes)")
    print("📊 Controle via PLC + backup teclado")
    print("=" * 50)
    
    rtsp_url = "rtsp://DaniloLira:Danilo%4034333528@192.168.0.100:554/stream2"
    
    detector = DetectorSimplesPlc(rtsp_url)
    
    if not detector.conectar_camera():
        print("❌ FALHA NA CÂMERA")
        return
    
    if detector.plc_conectado and detector.db18_disponivel:
        print("✅ Sistema completo - PLC + Visual")
    elif detector.plc_conectado:
        print("⚠️ PLC OK, mas DB18 indisponível")
    else:
        print("❌ PLC OFF - apenas visual")
    
    try:
        detector.executar()
    except KeyboardInterrupt:
        print("Sistema finalizado!")

if __name__ == "__main__":
    main()