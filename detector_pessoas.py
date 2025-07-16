import cv2
import time
import numpy as np
from ultralytics import YOLO
import math
import threading
from queue import Queue
import snap7
import struct

class DetectorPessoasInteligente:
    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.cap = None
        self.yolo_model = None
        self.confianca_minima = 0.7
        
        # ÁREA CENTRAL AUTOMÁTICA
        self.area_coords = None
        
        # DETECÇÃO E TRACKING PARA VELOCIDADE
        self.pessoas_detectadas = []
        self.pessoas_anteriores = []
        self.processando = False
        
        # PERFORMANCE
        self.frame_skip = 2
        self.frame_count = 0
        self.fps_real = 30
        self.tempo_ultimo_frame = time.time()
        
        # QUEUES OTIMIZADAS
        self.queue_frame = Queue(maxsize=1)
        self.queue_resultado = Queue(maxsize=1)
        self.ativo = True
        
        # PARÂMETROS DE MEDIÇÃO
        self.altura_pessoa_real = 170  # cm
        self.focal_length = 800  # calibrar conforme sua câmera
        
        # ====== PLC SIEMENS S7-1500 ======
        self.plc = snap7.client.Client()
        self.plc_ip = "192.168.0.33"
        self.plc_rack = 0
        self.plc_slot = 1
        self.db_number = 17  # DB17 conforme sua configuração
        self.plc_conectado = False
        self.ultimo_estado_enviado = False
        
        # Conectar PLC
        self.conectar_plc()
        
    def conectar_plc(self):
        """Conectar ao PLC Siemens S7-1500"""
        try:
            print(f"🔌 Conectando ao PLC {self.plc_ip}...")
            self.plc.connect(self.plc_ip, self.plc_rack, self.plc_slot)
            self.plc_conectado = True
            print("✅ PLC conectado com sucesso!")
            
            # Teste inicial - escrever que sistema está funcionando
            self.escrever_sistema_funcionando(True)
            
        except Exception as e:
            print(f"⚠️ Erro conectando PLC: {e}")
            self.plc_conectado = False
    
    def reconectar_plc(self):
        """Tentar reconectar ao PLC"""
        if self.plc_conectado:
            return
            
        try:
            print("🔄 Tentando reconectar PLC...")
            self.plc.disconnect()
            time.sleep(1)
            self.plc.connect(self.plc_ip, self.plc_rack, self.plc_slot)
            self.plc_conectado = True
            print("✅ PLC reconectado!")
        except Exception as e:
            print(f"❌ Falha na reconexão: {e}")
            self.plc_conectado = False
    
    def escrever_sistema_funcionando(self, status):
        """Escrever status do sistema no PLC (DB17.DBX16.0)"""
        if not self.plc_conectado:
            return False
            
        try:
            # Ler byte atual do offset 16
            data = self.plc.db_read(self.db_number, 16, 1)
            
            # Modificar bit 0
            if status:
                data[0] = data[0] | 0x01  # Setar bit 0
            else:
                data[0] = data[0] & 0xFE  # Limpar bit 0
            
            # Escrever de volta
            self.plc.db_write(self.db_number, 16, data)
            return True
            
        except Exception as e:
            print(f"❌ Erro escrevendo sistema funcionando: {e}")
            self.plc_conectado = False
            return False
    
    def enviar_dados_plc(self, pessoas_detectadas):
        """Enviar dados para PLC DB17"""
        if not self.plc_conectado:
            # Tentar reconectar
            self.reconectar_plc()
            return
        
        try:
            tem_pessoas = len(pessoas_detectadas) > 0
            quantidade_pessoas = len(pessoas_detectadas)
            
            # Só enviar se mudou o estado (otimização)
            if tem_pessoas != self.ultimo_estado_enviado:
                
                # 1. BOOL - Pessoa Detectada (DB17.DBX0.0)
                data_bool = bytearray(1)
                if tem_pessoas:
                    data_bool[0] = 0x01
                else:
                    data_bool[0] = 0x00
                self.plc.db_write(self.db_number, 0, data_bool)
                
                # 2. INT - Quantidade de Pessoas (DB17.DBW2)
                data_int = struct.pack('>H', quantidade_pessoas)  # Big endian, unsigned short
                self.plc.db_write(self.db_number, 2, data_int)
                
                print(f"📤 PLC: Pessoas={tem_pessoas}, Qtd={quantidade_pessoas}")
                self.ultimo_estado_enviado = tem_pessoas
            
            # Sempre atualizar distância e velocidade se tem pessoas
            if tem_pessoas:
                # Calcular distância mínima
                distancia_min = min(p['distancia'] for p in pessoas_detectadas if p['distancia'] > 0)
                
                # Calcular velocidade máxima
                velocidade_max = max(p['velocidade'] for p in pessoas_detectadas)
                
                # 3. REAL - Distância Mínima (DB17.DBD4)
                data_real_dist = struct.pack('>f', distancia_min)  # Big endian float
                self.plc.db_write(self.db_number, 4, data_real_dist)
                
                # 4. REAL - Velocidade Máxima (DB17.DBD8)
                data_real_vel = struct.pack('>f', velocidade_max)  # Big endian float
                self.plc.db_write(self.db_number, 8, data_real_vel)
                
                # Log detalhado quando há movimento
                if velocidade_max > 0.1:
                    print(f"📊 Dist: {distancia_min:.1f}cm, Vel: {velocidade_max:.1f}km/h")
            
            # 5. DINT - Timestamp Unix (DB17.DBD12)
            timestamp = int(time.time())
            data_timestamp = struct.pack('>L', timestamp)  # Big endian unsigned long
            self.plc.db_write(self.db_number, 12, data_timestamp)
            
            # 6. BOOL - Sistema Funcionando (DB17.DBX16.0) - já feito na conexão
            
        except Exception as e:
            print(f"❌ Erro enviando dados PLC: {e}")
            self.plc_conectado = False
    
    def carregar_yolo(self):
        """Carregar YOLO otimizado"""
        print("🤖 Carregando YOLO...")
        
        try:
            self.yolo_model = YOLO('yolov8n.pt')
            self.yolo_model.overrides['verbose'] = False
            print("✅ YOLO carregado!")
            return True
        except Exception as e:
            print(f"❌ Erro: {e}")
            return False
    
    def conectar_camera(self):
        """Conectar câmera"""
        print("🔗 Conectando câmera...")
        
        self.cap = cv2.VideoCapture(self.rtsp_url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        if not self.cap.isOpened():
            print("❌ Falha na conexão!")
            return False
            
        print("✅ Câmera conectada!")
        return True
    
    def definir_area_centro(self, frame):
        """Definir área no centro automaticamente"""
        h, w = frame.shape[:2]
        
        # Área grande no centro (60% x 70%)
        largura = int(w * 0.6)
        altura = int(h * 0.7)
        
        x1 = (w - largura) // 2
        y1 = (h - altura) // 2
        x2 = x1 + largura
        y2 = y1 + altura
        
        self.area_coords = np.array([
            [x1, y1], [x2, y1], [x2, y2], [x1, y2]
        ], np.int32)
        
        print(f"✅ Área definida: {largura}x{altura} no centro")
    
    def dentro_da_area(self, x, y):
        """Verificar se ponto está na área"""
        if self.area_coords is None:
            return True
        
        x1, y1 = self.area_coords[0]
        x2, y2 = self.area_coords[2]
        
        return x1 <= x <= x2 and y1 <= y <= y2
    
    def calcular_distancia_real(self, altura_pixels):
        """Cálculo melhorado de distância real da câmera"""
        if altura_pixels > 30:  # Mínimo para ter precisão
            # Fórmula: Distância = (Altura_Real × Focal_Length) / Altura_Pixels
            distancia_cm = (self.altura_pessoa_real * self.focal_length) / altura_pixels
            return max(50, min(1000, distancia_cm))  # Limitar entre 50cm e 10m
        return 0
    
    def calcular_velocidade(self, pessoa_atual, pessoa_anterior, delta_tempo):
        """Calcular velocidade da pessoa em km/h"""
        if delta_tempo <= 0:
            return 0
        
        # Coordenadas dos centros
        x1, y1 = pessoa_atual['centro']
        x2, y2 = pessoa_anterior['centro']
        
        # Distância em pixels
        dist_pixels = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
        
        # Converter pixels para centímetros (aproximação)
        # Usar distância média para escala
        distancia_media = (pessoa_atual['distancia'] + pessoa_anterior['distancia']) / 2
        if distancia_media > 0:
            # Escala: pixels para cm baseado na distância
            escala_pixel_cm = distancia_media / 300  # 300px = distância de referência
            dist_cm = dist_pixels * escala_pixel_cm
            
            # Velocidade em cm/s, depois converter para km/h
            vel_cm_s = dist_cm / delta_tempo
            vel_km_h = (vel_cm_s * 3.6) / 100  # cm/s para km/h
            
            return max(0, min(50, vel_km_h))  # Limitar velocidade máxima
        
        return 0
    
    def encontrar_pessoa_correspondente(self, pessoa_atual, pessoas_anteriores):
        """Encontrar pessoa correspondente do frame anterior"""
        if not pessoas_anteriores:
            return None
        
        x1, y1 = pessoa_atual['centro']
        melhor_dist = float('inf')
        melhor_pessoa = None
        
        for pessoa_ant in pessoas_anteriores:
            x2, y2 = pessoa_ant['centro']
            dist = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
            
            # Se distância for razoável (pessoa não se moveu muito)
            if dist < 100 and dist < melhor_dist:  # Máximo 100 pixels de movimento
                melhor_dist = dist
                melhor_pessoa = pessoa_ant
        
        return melhor_pessoa
    
    def processar_yolo_async(self):
        """Processar YOLO em thread separada"""
        while self.ativo:
            try:
                if not self.queue_frame.empty():
                    frame_info = self.queue_frame.get(timeout=0.1)
                    frame = frame_info['frame']
                    tempo_frame = frame_info['tempo']
                    
                    # YOLO só para pessoas
                    results = self.yolo_model(frame, verbose=False, classes=[0])
                    
                    pessoas_agora = []
                    
                    for result in results:
                        boxes = result.boxes
                        if boxes is not None:
                            for box in boxes:
                                confianca = float(box.conf[0])
                                
                                if confianca >= self.confianca_minima:
                                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                                    
                                    # Escalar de volta para frame original
                                    x1, y1, x2, y2 = x1*2, y1*2, x2*2, y2*2
                                    
                                    centro_x = (x1 + x2) // 2
                                    centro_y = (y1 + y2) // 2
                                    
                                    if self.dentro_da_area(centro_x, centro_y):
                                        altura = y2 - y1
                                        distancia = self.calcular_distancia_real(altura)
                                        
                                        pessoa_atual = {
                                            'x': x1, 'y': y1, 'w': x2-x1, 'h': y2-y1,
                                            'centro': (centro_x, centro_y),
                                            'confianca': confianca,
                                            'distancia': distancia,
                                            'velocidade': 0,
                                            'tempo': tempo_frame
                                        }
                                        
                                        # Calcular velocidade comparando com frame anterior
                                        pessoa_anterior = self.encontrar_pessoa_correspondente(
                                            pessoa_atual, self.pessoas_anteriores
                                        )
                                        
                                        if pessoa_anterior:
                                            delta_tempo = tempo_frame - pessoa_anterior['tempo']
                                            velocidade = self.calcular_velocidade(
                                                pessoa_atual, pessoa_anterior, delta_tempo
                                            )
                                            pessoa_atual['velocidade'] = velocidade
                                        
                                        pessoas_agora.append(pessoa_atual)
                    
                    # Atualizar resultado
                    if not self.queue_resultado.full():
                        self.queue_resultado.put(pessoas_agora)
                    
                    self.processando = False
                    
            except Exception as e:
                print(f"Erro processamento: {e}")
                self.processando = False
    
    def heartbeat_plc(self):
        """Thread para manter conexão PLC viva"""
        while self.ativo:
            try:
                if self.plc_conectado:
                    # Enviar heartbeat a cada 10 segundos
                    self.escrever_sistema_funcionando(True)
                else:
                    # Tentar reconectar se desconectado
                    self.reconectar_plc()
                
                time.sleep(10)
                
            except Exception as e:
                print(f"❌ Erro heartbeat PLC: {e}")
                time.sleep(5)
    
    def desenhar_area(self, frame):
        """Desenhar área - visual limpo"""
        if self.area_coords is None:
            return
        
        pessoas_na_area = len(self.pessoas_detectadas)
        cor = (0, 0, 255) if pessoas_na_area > 0 else (0, 255, 0)
        
        # Contorno fino
        cv2.polylines(frame, [self.area_coords], True, cor, 1)
        
        # Status compacto - só mostra P: X ou LIVRE
        status = f"Area: {pessoas_na_area}" if pessoas_na_area > 0 else "AREA LIVRE"
        cv2.putText(frame, status, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor, 2)
        
        # ====== REMOVIDO: Status PLC, data/hora, FPS, DB17 ======
        # Essas informações foram removidas da tela conforme solicitado
        # Mas continuam funcionando internamente para o PLC
    
    def desenhar_pessoas(self, frame):
        """Desenhar pessoas - informações compactas"""
        for i, pessoa in enumerate(self.pessoas_detectadas):
            x, y, w, h = pessoa['x'], pessoa['y'], pessoa['w'], pessoa['h']
            distancia = pessoa['distancia']
            velocidade = pessoa['velocidade']
            
            # Cor baseada na distância
            if distancia < 100:
                cor = (0, 0, 255)  # Vermelho - muito perto
            elif distancia < 200:
                cor = (0, 165, 255)  # Laranja - perto
            else:
                cor = (0, 255, 0)  # Verde - longe
            
            # Caixa fina
            cv2.rectangle(frame, (x, y), (x + w, y + h), cor, 1)
            
            # ID compacto - MANTIDO conforme solicitado
            id_texto = f"Pessoa{i+1}"
            cv2.putText(frame, id_texto, (x, y - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)
            
            # Distância compacta
            if distancia > 0:
                dist_texto = f"{distancia:.0f}cm"
                cv2.putText(frame, dist_texto, (x, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 1)
            
            # Velocidade compacta
            if velocidade > 0.1:  # Só mostrar se tiver movimento significativo
                vel_texto = f"{velocidade:.1f}km/h"
                cv2.putText(frame, vel_texto, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 1)
            
            # Centro pequeno
            cv2.circle(frame, pessoa['centro'], 3, cor, -1)
    
    def executar(self):
        """Executar sistema melhorado"""
        print("🚀 DETECTOR OTIMIZADO - DISTÂNCIA + VELOCIDADE + PLC")
        print("ESC = Sair | ESPAÇO = Pausar")
        
        # Definir área
        ret, frame_inicial = self.cap.read()
        if ret:
            self.definir_area_centro(frame_inicial)
        
        # Thread de processamento YOLO
        thread_yolo = threading.Thread(target=self.processar_yolo_async)
        thread_yolo.daemon = True
        thread_yolo.start()
        
        # Thread de heartbeat PLC
        thread_plc = threading.Thread(target=self.heartbeat_plc)
        thread_plc.daemon = True
        thread_plc.start()
        
        pausado = False
        fps_count = 0
        
        while True:
            if not pausado:
                ret, frame = self.cap.read()
                if not ret:
                    continue
                
                tempo_atual = time.time()
                self.frame_count += 1
                
                # Atualizar FPS SIMPLES - só evitar divisão por zero
                if self.frame_count > 1:
                    delta_tempo = tempo_atual - self.tempo_ultimo_frame
                    if delta_tempo > 0.001:  # Evitar divisão por zero
                        self.fps_real = 1.0 / delta_tempo
                
                self.tempo_ultimo_frame = tempo_atual
                
                # Processar frame
                if self.frame_count % self.frame_skip == 0 and not self.processando:
                    frame_pequeno = cv2.resize(frame, (frame.shape[1]//2, frame.shape[0]//2))
                    
                    # Limpar queue antiga
                    while not self.queue_frame.empty():
                        self.queue_frame.get()
                    
                    if not self.queue_frame.full():
                        frame_info = {
                            'frame': frame_pequeno,
                            'tempo': tempo_atual
                        }
                        self.queue_frame.put(frame_info)
                        self.processando = True
                
                # Pegar resultado mais recente
                while not self.queue_resultado.empty():
                    # Salvar estado anterior antes de atualizar
                    self.pessoas_anteriores = self.pessoas_detectadas.copy()
                    self.pessoas_detectadas = self.queue_resultado.get()
                    
                    # ====== ENVIAR DADOS PARA PLC ======
                    self.enviar_dados_plc(self.pessoas_detectadas)
                
                # Desenhar tudo
                self.desenhar_area(frame)
                self.desenhar_pessoas(frame)
                
                # ====== REMOVIDO: Informações da tela ======
                # Tempo, FPS, DB17 removidos da tela conforme solicitado
                # pessoas_count = len(self.pessoas_detectadas)
                # tempo_str = time.strftime("%H:%M:%S")
                # cv2.putText(frame, f"{tempo_str}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                # cv2.putText(frame, f"FPS: {self.fps_real:.1f}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                # cv2.putText(frame, f"DB{self.db_number}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Log periódico - ainda funciona no console
                fps_count += 1
                if fps_count % 90 == 0:  # A cada 3 segundos
                    pessoas_count = len(self.pessoas_detectadas)
                    print(f"FPS: {self.fps_real:.1f} | Pessoas: {pessoas_count} | PLC: {'✅' if self.plc_conectado else '❌'}")
                    if pessoas_count > 0:
                        for i, p in enumerate(self.pessoas_detectadas):
                            print(f"  P{i+1}: {p['distancia']:.0f}cm, {p['velocidade']:.1f}km/h")
                
                cv2.imshow('Danilio Lira - Detector', frame)
            
            # Controles
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27:  # ESC
                break
            elif key == ord(' '):  # ESPAÇO
                pausado = not pausado
                print("PAUSADO" if pausado else "RODANDO")
        
        # Finalizar
        self.ativo = False
        
        # Avisar PLC que sistema está parando
        if self.plc_conectado:
            self.escrever_sistema_funcionando(False)
            self.plc.disconnect()
        
        self.cap.release()
        cv2.destroyAllWindows()
        print("Sistema finalizado!")

def main():
    print("🤖 DETECTOR MELHORADO + PLC SIEMENS S7-1500")
    print("📏 Medição de distância real da câmera")
    print("🏃 Cálculo de velocidade em tempo real")
    print("🔌 Comunicação direta com PLC via snap7")
    print("📊 DataBlock DB17 - IP: 192.168.0.33")
    print("=" * 50)
    
    rtsp_url = "rtsp://DaniloLira:Danilo%4034333528@192.168.0.100:554/stream2"
    
    detector = DetectorPessoasInteligente(rtsp_url)
    
    if not detector.carregar_yolo():
        return
    
    if not detector.conectar_camera():
        return
    
    try:
        detector.executar()
    except KeyboardInterrupt:
        print("Interrompido")

if __name__ == "__main__":
    main()