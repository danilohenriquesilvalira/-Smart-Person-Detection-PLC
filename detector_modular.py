import cv2
import time
import numpy as np
import os
import shutil
import threading
from collections import Counter

# STREAMING INTEGRADO
from flask import Flask, Response
from flask_cors import CORS
from waitress import serve

# Importar módulos
from plc_manager import PLCManager
from websocket_server import WebSocketServer, create_data_structure

# CAMERA MANAGER COM STREAMING INTEGRADO
class CameraManager:
    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.cap = None
        self.area_coords = None
        self.tamanho_area = 200
        self.frame_atual = None
        
        # STREAMING - Variáveis do video_stream_standalone.py
        self.current_frame = None
        self.is_camera_running = False
        self.frame_lock = threading.Lock()
        
        # Flask para streaming
        self.flask_app = Flask(__name__)
        CORS(self.flask_app)
        self.stream_thread = None
        
        # Configurar rota Flask
        @self.flask_app.route('/video_feed')
        def video_feed():
            return Response(self.generate_mjpeg_frames(),
                            mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def conectar(self):
        """Conectar à câmera E iniciar streaming"""
        # Conectar câmera
        self.cap = cv2.VideoCapture(self.rtsp_url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not self.cap.isOpened():
            return False
        
        # INICIAR STREAMING automaticamente
        self.is_camera_running = True
        self.start_streaming()
        
        return True
    
    def start_streaming(self):
        """Iniciar servidor Flask para streaming"""
        # Thread para servidor Flask
        self.stream_thread = threading.Thread(target=self._start_flask_server, daemon=True)
        self.stream_thread.start()
        print(f"🎥 Streaming iniciado: http://localhost:5000/video_feed")
    
    def _start_flask_server(self):
        """Servidor Flask - exatamente como video_stream_standalone.py"""
        try:
            # Desabilitar logs do Flask
            import logging
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)
            
            serve(self.flask_app, host='0.0.0.0', port=5000, threads=4)
        except Exception as e:
            print(f"❌ Erro no servidor Flask: {e}")
    
    def generate_mjpeg_frames(self):
        """Gerar frames para streaming - IGUAL ao video_stream_standalone.py"""
        while self.is_camera_running:
            frame = self.get_current_frame()
            if frame is None:
                time.sleep(0.1)
                continue

            # Se ROI não definida, definir
            if self.area_coords is None:
                self.definir_area(frame)
            
            try:
                # DESENHAR RETÂNGULO AMARELO - igual ao original
                self.desenhar_area_streaming(frame, cor=(0, 255, 255))

                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if not ret:
                    time.sleep(0.1)
                    continue

                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                time.sleep(0.03)

            except Exception as e:
                print(f"❌ Erro no streaming: {e}")
                time.sleep(0.1)
    
    def get_current_frame(self):
        """Obter frame atual thread-safe"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def desenhar_area_streaming(self, frame, cor=(0, 255, 255)):
        """Desenhar área para streaming - IGUAL ao video_stream_standalone.py"""
        if self.area_coords is None:
            return
        
        x1, y1, x2, y2 = self.area_coords
        cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 3)
        
        centro_x, centro_y = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.line(frame, (centro_x - 20, centro_y), (centro_x + 20, centro_y), cor, 2)
        cv2.line(frame, (centro_x, centro_y - 20), (centro_x, centro_y + 20), cor, 2)
    
    def ler_frame(self):
        """Ler frame da câmera"""
        if not self.cap:
            return False, None
        
        ret, frame = self.cap.read()
        if ret:
            # Atualizar AMBOS frames
            self.frame_atual = frame
            
            with self.frame_lock:
                self.current_frame = frame.copy()
            
            if self.area_coords is None:
                self.definir_area(frame)
        
        return ret, frame
    
    def definir_area(self, frame):
        """Definir área central de detecção"""
        h, w = frame.shape[:2]
        centro_x, centro_y = w // 2, h // 2
        meio = self.tamanho_area // 2
        self.area_coords = (centro_x - meio, centro_y - meio, centro_x + meio, centro_y + meio)
    
    def extrair_area(self, frame):
        """Extrair área de interesse do frame"""
        if self.area_coords is None:
            return None
        
        x1, y1, x2, y2 = self.area_coords
        area = frame[y1:y2, x1:x2]
        if len(area.shape) == 3:
            area = cv2.cvtColor(area, cv2.COLOR_BGR2GRAY)
        return cv2.resize(area, (100, 100))
    
    def desenhar_area(self, frame, cor=(255, 100, 0)):
        """Desenhar área de detecção no frame OpenCV"""
        if self.area_coords is None:
            return
        
        x1, y1, x2, y2 = self.area_coords
        cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 3)
        
        centro_x, centro_y = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.line(frame, (centro_x - 20, centro_y), (centro_x + 20, centro_y), cor, 2)
        cv2.line(frame, (centro_x, centro_y - 20), (centro_x, centro_y + 20), cor, 2)
    
    def desconectar(self):
        """Desconectar câmera e parar streaming"""
        self.is_camera_running = False
        
        if self.cap:
            self.cap.release()
            self.cap = None


class DetectorModular:
    def __init__(self, rtsp_url, websocket_port=8765):
        # Componentes principais
        self.camera = CameraManager(rtsp_url)
        self.plc = PLCManager()
        self.websocket = WebSocketServer(port=websocket_port)
        
        # Dados de treinamento
        self.pasta_dados = "dados_copo"
        self.fotos_sem_copo = []
        self.fotos_copo_bom = []
        self.fotos_copo_danificado = []
        
        # Contadores
        self.contador_sem_copo = 0
        self.contador_copo_bom = 0
        self.contador_copo_danificado = 0
        self.max_fotos = 10
        
        # Estado
        self.modo_atual = "AGUARDANDO"
        self.estado_detectado = "SEM_COPO"
        self.treinamento_completo = False
        self.sensibilidade = 0.1
        self.ultima_captura = 0
        
        # Valores medidos
        self.valor_sem_copo = 0.0
        self.valor_copo_bom = 0.0
        self.valor_copo_danificado = 0.0
        
        # Histórico para estabilidade
        self.historico = []
        
        # Inicializar sistema
        self._inicializar()
    
    def _inicializar(self):
        """Inicializar todos os componentes"""
        print("🚀 Inicializando sistema modular...")
        
        # Criar pastas
        self.criar_pastas()
        
        # Carregar fotos existentes
        self.carregar_fotos()
        
        # Conectar componentes
        camera_ok = self.camera.conectar()
        plc_ok = self.plc.conectar()
        
        # Iniciar WebSocket COM CALLBACKS
        self.websocket.start_server()
        self._configurar_websocket_callbacks()
        
        print(f"📷 Câmera: {'✅' if camera_ok else '❌'}")
        print(f"🔌 PLC: {'✅' if plc_ok else '❌'}")
        print(f"🌐 WebSocket: ✅ Porta {self.websocket.port}")
        print(f"📱 Dashboard: ✅ Controles ativos")
    
    def _configurar_websocket_callbacks(self):
        """Configurar callbacks para comandos do Dashboard"""
        self.websocket.set_command_callback('train', self._cmd_treinar)
        self.websocket.set_command_callback('detect', self._cmd_detectar)
        self.websocket.set_command_callback('reset', self._cmd_reset)
        self.websocket.set_command_callback('capture_empty', self._cmd_capturar_sem_copo)
        self.websocket.set_command_callback('capture_good', self._cmd_capturar_copo_bom)
        self.websocket.set_command_callback('capture_damaged', self._cmd_capturar_danificado)
    
    # COMANDOS VIA DASHBOARD
    def _cmd_treinar(self, cmd):
        self.modo_atual = "TREINAMENTO"
        print("📱 DASHBOARD: TREINAR")
        return True
    
    def _cmd_detectar(self, cmd):
        if self.treinamento_completo:
            self.modo_atual = "DETECCAO"
            print("📱 DASHBOARD: DETECTAR")
            return True
        return False
    
    def _cmd_reset(self, cmd):
        self.reset_sistema()
        print("📱 DASHBOARD: RESET")
        return True
    
    def _cmd_capturar_sem_copo(self, cmd):
        if self.modo_atual == "TREINAMENTO":
            return self.capturar_foto("sem_copo")
        return False
    
    def _cmd_capturar_copo_bom(self, cmd):
        if self.modo_atual == "TREINAMENTO":
            return self.capturar_foto("copo_bom")
        return False
    
    def _cmd_capturar_danificado(self, cmd):
        if self.modo_atual == "TREINAMENTO":
            return self.capturar_foto("copo_danificado")
        return False
    
    def criar_pastas(self):
        """Criar estrutura de pastas"""
        pastas = [
            self.pasta_dados,
            os.path.join(self.pasta_dados, "sem_copo"),
            os.path.join(self.pasta_dados, "copo_bom"),
            os.path.join(self.pasta_dados, "copo_danificado")
        ]
        for pasta in pastas:
            os.makedirs(pasta, exist_ok=True)
    
    def carregar_fotos(self):
        """Carregar fotos existentes"""
        estados = [
            ("sem_copo", self.fotos_sem_copo),
            ("copo_bom", self.fotos_copo_bom),
            ("copo_danificado", self.fotos_copo_danificado)
        ]
        
        for pasta_nome, lista_fotos in estados:
            pasta_path = os.path.join(self.pasta_dados, pasta_nome)
            for arquivo in sorted(os.listdir(pasta_path)):
                if arquivo.endswith('.jpg'):
                    img_path = os.path.join(pasta_path, arquivo)
                    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        img = cv2.resize(img, (100, 100))
                        lista_fotos.append(img)
        
        # Atualizar contadores
        self.contador_sem_copo = len(self.fotos_sem_copo)
        self.contador_copo_bom = len(self.fotos_copo_bom)
        self.contador_copo_danificado = len(self.fotos_copo_danificado)
        
        # Verificar completude
        self.verificar_treinamento_completo()
    
    def verificar_treinamento_completo(self):
        """Verificar se treinamento está completo"""
        completo = (self.contador_sem_copo >= self.max_fotos and 
                    self.contador_copo_bom >= self.max_fotos and
                    self.contador_copo_danificado >= self.max_fotos)
        
        if completo and not self.treinamento_completo:
            self.treinamento_completo = True
            print("🎉 TREINAMENTO COMPLETO!")
    
    def processar_comandos_plc(self):
        """Processar comandos do PLC"""
        comandos = self.plc.ler_comandos()
        if not comandos:
            return
        
        # Atualizar sensibilidade
        if comandos.get('sensibilidade') != self.sensibilidade:
            self.sensibilidade = comandos['sensibilidade']
            print(f"📡 PLC: Sensibilidade {self.sensibilidade:.3f}")
        
        # Processar comandos
        if comandos.get('treinar'):
            self.modo_atual = "TREINAMENTO"
            print("📡 PLC: TREINAR")
        
        if comandos.get('detectar') and self.treinamento_completo:
            self.modo_atual = "DETECCAO"
            print("🎯 PLC: DETECTAR")
        
        if comandos.get('reset'):
            self.reset_sistema()
            print("🔄 PLC: RESET")
        
        # Capturas durante treinamento
        if self.modo_atual == "TREINAMENTO":
            if comandos.get('capturar_sem_copo'):
                self.capturar_foto("sem_copo")
            if comandos.get('capturar_copo_bom'):
                self.capturar_foto("copo_bom")
            if comandos.get('capturar_danificado'):
                self.capturar_foto("copo_danificado")
    
    def capturar_foto(self, categoria):
        """Capturar foto para treinamento"""
        if not hasattr(self.camera, 'frame_atual') or self.camera.frame_atual is None:
            return False
        
        # Evitar capturas muito próximas
        agora = time.time()
        if agora - self.ultima_captura < 1.0:
            return False
        
        # Extrair área
        area = self.camera.extrair_area(self.camera.frame_atual)
        if area is None:
            return False
        
        # Salvar baseado na categoria
        if categoria == "sem_copo" and self.contador_sem_copo < self.max_fotos:
            self.contador_sem_copo += 1
            self.fotos_sem_copo.append(area)
            contador = self.contador_sem_copo
        elif categoria == "copo_bom" and self.contador_copo_bom < self.max_fotos:
            self.contador_copo_bom += 1
            self.fotos_copo_bom.append(area)
            contador = self.contador_copo_bom
        elif categoria == "copo_danificado" and self.contador_copo_danificado < self.max_fotos:
            self.contador_copo_danificado += 1
            self.fotos_copo_danificado.append(area)
            contador = self.contador_copo_danificado
        else:
            return False
        
        # Salvar arquivo
        nome = f"{categoria}_{contador:02d}.jpg"
        pasta = os.path.join(self.pasta_dados, categoria)
        cv2.imwrite(os.path.join(pasta, nome), area)
        
        self.verificar_treinamento_completo()
        self.ultima_captura = agora
        print(f"📸 Capturado: {categoria} ({contador}/10)")
        return True
    
    def medir_valores(self, frame):
        """Medir valores de similaridade"""
        if not self.treinamento_completo:
            return
        
        area = self.camera.extrair_area(frame)
        if area is None:
            return
        
        self.valor_sem_copo = self.calcular_similaridade(area, self.fotos_sem_copo)
        self.valor_copo_bom = self.calcular_similaridade(area, self.fotos_copo_bom)
        self.valor_copo_danificado = self.calcular_similaridade(area, self.fotos_copo_danificado)
    
    def calcular_similaridade(self, area_atual, fotos_estado):
        """Calcular similaridade usando template matching"""
        if not fotos_estado:
            return 0.0
        
        similarities = []
        for foto in fotos_estado:
            resultado = cv2.matchTemplate(area_atual, foto, cv2.TM_CCOEFF_NORMED)
            _, similarity, _, _ = cv2.minMaxLoc(resultado)
            similarities.append(similarity)
        
        # Média das 3 melhores similaridades
        similarities.sort(reverse=True)
        top_similarities = similarities[:3] if len(similarities) >= 3 else similarities
        return np.mean(top_similarities)
    
    def detectar_estado(self):
        """Detectar estado atual"""
        if not self.treinamento_completo:
            return None
        
        # Encontrar maior valor
        valores = {
            "SEM_COPO": self.valor_sem_copo,
            "COPO_BOM": self.valor_copo_bom,
            "COPO_DANIFICADO": self.valor_copo_danificado
        }
        
        ordenados = sorted(valores.items(), key=lambda x: x[1], reverse=True)
        primeiro_estado, primeiro_valor = ordenados[0]
        segundo_estado, segundo_valor = ordenados[1]
        
        diferenca = primeiro_valor - segundo_valor
        
        # Aplicar sensibilidade
        if diferenca >= self.sensibilidade:
            return primeiro_estado
        else:
            return None  # Incerto
    
    def aplicar_estabilidade(self, deteccao_atual):
        """Aplicar filtro de estabilidade"""
        if deteccao_atual is None:
            return self.estado_detectado
        
        self.historico.append(deteccao_atual)
        if len(self.historico) > 3:
            self.historico.pop(0)
        
        if len(self.historico) >= 2:
            contador = Counter(self.historico)
            mais_comum, ocorrencias = contador.most_common(1)[0]
            
            if ocorrencias >= 2:
                return mais_comum
        
        return self.estado_detectado
    
    def reset_sistema(self):
        """Reset completo do sistema"""
        # Resetar dados
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
        for pasta in ["sem_copo", "copo_bom", "copo_danificado"]:
            pasta_path = os.path.join(self.pasta_dados, pasta)
            if os.path.exists(pasta_path):
                shutil.rmtree(pasta_path)
                os.makedirs(pasta_path)
        
        print("🔄 Sistema resetado")
    
    def atualizar_websocket(self):
        """Atualizar dados do WebSocket"""
        data = create_data_structure(
            status=self.modo_atual,
            estado=self.estado_detectado,
            valores={
                "sem_copo": self.valor_sem_copo,
                "copo_bom": self.valor_copo_bom,
                "copo_danificado": self.valor_copo_danificado
            },
            contadores={
                "sem_copo": self.contador_sem_copo,
                "copo_bom": self.contador_copo_bom,
                "copo_danificado": self.contador_copo_danificado
            },
            plc_status={
                "conectado": self.plc.conectado,
                "db18_disponivel": self.plc.db18_disponivel
            }
        )
        data["sensibilidade"] = self.sensibilidade
        data["treinamento_completo"] = self.treinamento_completo
        
        # DADOS PARA DASHBOARD
        data["controles"] = {
            "pode_treinar": True,
            "pode_detectar": self.treinamento_completo,
            "pode_capturar": self.modo_atual == "TREINAMENTO"
        }
        
        self.websocket.update_data(data)
    
    def desenhar_interface(self, frame):
        """Desenhar interface visual (agora apenas para o frame a ser processado internamente, se necessário para debug ou log)"""
        # This method is designed to draw on the 'frame' which would then be displayed by cv2.imshow.
        # Since we are removing cv2.imshow, the visual interface drawn here won't be visible to the user
        # unless you re-purpose this method to save frames or to perform some other visual logging.
        # For the purpose of removing the local window, this method effectively becomes a no-op
        # in terms of user-facing visual output, but it's kept for logical completeness in the code
        # in case you decide to re-implement some form of visual logging later.
        pass

    def desenhar_barra(self, frame, x, y, largura, altura, valor, cor, label):
        """Desenhar barra de progresso (no-op since interface is not displayed)"""
        pass
    
    def processar_teclado(self, key):
        """Processar comandos do teclado"""
        if key == ord('t'):
            self.modo_atual = "TREINAMENTO"
            print("⌨️ Teclado: TREINAMENTO")
        elif key == ord('d') and self.treinamento_completo:
            self.modo_atual = "DETECCAO"
            print("⌨️ Teclado: DETECÇÃO")
        elif key == ord('r'):
            self.reset_sistema()
        elif key == ord('v') and self.modo_atual == "TREINAMENTO":
            self.capturar_foto("sem_copo")
        elif key == ord('c') and self.modo_atual == "TREINAMENTO":
            self.capturar_foto("copo_bom")
        elif key == ord('s') and self.modo_atual == "TREINAMENTO":
            self.capturar_foto("copo_danificado")
    
    def executar(self):
        """Loop principal do sistema"""
        print("🚀 SISTEMA MODULAR + STREAMING + DASHBOARD INICIADO")
        print(f"🌐 WebSocket: ws://localhost:{self.websocket.port}")
        print(f"🎥 Streaming: http://localhost:5000/video_feed")
        print(f"📱 Dashboard: Controles via web ativos")
        print("=" * 60)
        
        contador_ciclos = 0
        
        try:
            while True:
                # Ler frame da câmera
                ret, frame = self.camera.ler_frame()
                if not ret:
                    continue
                
                # Comunicação PLC (a cada 100ms)
                if contador_ciclos % 3 == 0:
                    self.processar_comandos_plc()
                    
                    # Enviar dados para PLC
                    if self.plc.conectado and self.plc.db18_disponivel:
                        if self.treinamento_completo:
                            self.plc.enviar_valores(
                                self.valor_sem_copo,
                                self.valor_copo_bom,
                                self.valor_copo_danificado
                            )
                        
                        self.plc.enviar_status(
                            self.treinamento_completo,
                            self.contador_sem_copo,
                            self.contador_copo_bom,
                            self.contador_copo_danificado,
                            self.estado_detectado
                        )
                
                # Detecção (se treinamento completo)
                if self.treinamento_completo:
                    self.medir_valores(frame)
                    
                    if self.modo_atual == "DETECCAO":
                        deteccao_atual = self.detectar_estado()
                        estado_estavel = self.aplicar_estabilidade(deteccao_atual)
                        
                        if estado_estavel != self.estado_detectado:
                            self.estado_detectado = estado_estavel
                            # Enviar para DB17 (compatibilidade)
                            self.plc.enviar_db17_compatibilidade(estado_estavel)
                            print(f"🎯 Estado: {estado_estavel}")
                
                # Atualizar WebSocket (a cada 200ms)
                if contador_ciclos % 6 == 0:
                    self.atualizar_websocket()
                
                # Interface visual - Removed cv2.imshow, so this will no longer be visible.
                # However, you might still want to call this if you were performing some
                # internal drawing for debugging or logging that doesn't need to be displayed.
                # Since the request is to remove the window, the drawing functions can be
                # effectively made into no-ops or removed if they serve no other purpose.
                # For safety, I've kept the call but made the methods "pass" (do nothing).
                self.desenhar_interface(frame) 
                
                # No longer need to process keyboard input since there's no window
                # that would be in focus to receive key presses.
                # However, I'll keep the `processar_teclado` method for completeness,
                # as the prompt asked to remove the window, not necessarily keyboard control.
                # If you decide to completely remove keyboard control, you can delete this section.
                # key = cv2.waitKey(1) & 0xFF
                # if key == 27:  # ESC
                #     break
                # elif key != 255:
                #     self.processar_teclado(key)
                
                # Instead of waiting for a key press, we can just sleep to control loop speed
                time.sleep(0.03) # Adjust this value if needed for desired loop frequency

                contador_ciclos += 1
        
        except KeyboardInterrupt:
            print("\n🛑 Sistema interrompido")
        
        finally:
            self.finalizar()
    
    def finalizar(self):
        """Finalizar sistema"""
        print("🛑 Finalizando sistema...")
        
        # Desconectar componentes
        self.camera.desconectar()
        self.plc.desconectar()
        self.websocket.stop_server()
        
        # Close all OpenCV windows (though there shouldn't be any now)
        cv2.destroyAllWindows()
        
        print("✅ Sistema finalizado")

def main():
    """Função principal"""
    print("🥤 DETECTOR MODULAR + PLC + WEBSOCKET + STREAMING + DASHBOARD")
    print("🔧 Controle: PLC + Teclado + Dashboard Web")
    print("🌐 Streaming + WebSocket integrados")
    print("=" * 60)
    
    # Configurações
    rtsp_url = "rtsp://DaniloLira:Danilo%4034333528@192.168.0.100:554/stream2"
    websocket_port = 8765
    
    # Inicializar detector
    detector = DetectorModular(rtsp_url, websocket_port)
    
    # Verificar componentes
    if not detector.camera.cap or not detector.camera.cap.isOpened():
        print("❌ FALHA NA CÂMERA")
        return
    
    print(f"📷 Câmera: ✅")
    print(f"🔌 PLC: {'✅' if detector.plc.conectado else '❌'}")
    print(f"🌐 WebSocket: ✅ ws://localhost:{websocket_port}")
    print(f"🎥 Streaming: ✅ http://localhost:5000/video_feed")
    print(f"📱 Dashboard: ✅ Controles web ativos")
    
    # Executar sistema
    detector.executar()

if __name__ == "__main__":
    main()