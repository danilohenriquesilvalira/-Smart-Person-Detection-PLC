import cv2
import time
import numpy as np
import os
import shutil
from collections import Counter

# Importar módulos
from camera_manager import CameraManager
from plc_manager import PLCManager
from websocket_server import WebSocketServer, create_data_structure

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
        
        # Iniciar WebSocket
        self.websocket.start_server()
        
        print(f"📷 Câmera: {'✅' if camera_ok else '❌'}")
        print(f"🔌 PLC: {'✅' if plc_ok else '❌'}")
        print(f"🌐 WebSocket: ✅ Porta {self.websocket.port}")
    
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
            print("📚 PLC: TREINAR")
        
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
        
        self.websocket.update_data(data)
    
    def desenhar_interface(self, frame):
        """Desenhar interface visual"""
        # Painel lateral direito
        painel_x = frame.shape[1] - 400
        painel_y = 50
        painel_w = 380
        painel_h = 550
        
        # Fundo do painel
        overlay = frame.copy()
        cv2.rectangle(overlay, (painel_x, painel_y), (painel_x + painel_w, painel_y + painel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        cv2.rectangle(frame, (painel_x, painel_y), (painel_x + painel_w, painel_y + painel_h), (255, 255, 255), 3)
        
        # Título
        cv2.putText(frame, "DETECTOR MODULAR", (painel_x + 20, painel_y + 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        y_pos = painel_y + 80
        
        # Status principal
        cores_status = {
            "AGUARDANDO": (255, 255, 0),
            "TREINAMENTO": (0, 255, 255),
            "DETECCAO": (0, 255, 0) if self.estado_detectado == "COPO_BOM" else 
                       (0, 0, 255) if self.estado_detectado == "COPO_DANIFICADO" else (128, 128, 128)
        }
        
        cor_status = cores_status.get(self.modo_atual, (255, 255, 255))
        cv2.putText(frame, f"STATUS: {self.modo_atual}", (painel_x + 20, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor_status, 2)
        y_pos += 40
        
        # Estado detectado
        if self.modo_atual == "DETECCAO":
            cor_estado = (0, 255, 0) if self.estado_detectado == "COPO_BOM" else \
                        (0, 0, 255) if self.estado_detectado == "COPO_DANIFICADO" else (128, 128, 128)
            cv2.putText(frame, f"ESTADO: {self.estado_detectado}", (painel_x + 20, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor_estado, 2)
        y_pos += 50
        
        # Sensibilidade
        cv2.putText(frame, f"SENSIBILIDADE: {self.sensibilidade:.3f}", (painel_x + 20, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        y_pos += 40
        
        # Valores medidos (se treinamento completo)
        if self.treinamento_completo:
            cv2.putText(frame, "VALORES MEDIDOS:", (painel_x + 20, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_pos += 40
            
            # Barras de valores
            barra_w = 300
            barra_h = 25
            
            valores_barras = [
                ("SEM COPO", self.valor_sem_copo, (128, 128, 128)),
                ("COPO BOM", self.valor_copo_bom, (0, 255, 0)),
                ("DANIFICADO", self.valor_copo_danificado, (0, 0, 255))
            ]
            
            for nome, valor, cor in valores_barras:
                self.desenhar_barra(frame, painel_x + 20, y_pos, barra_w, barra_h, valor, cor, nome)
                y_pos += 50
        
        # Contadores de treinamento
        y_pos = painel_y + painel_h - 180
        cv2.putText(frame, "TREINAMENTO:", (painel_x + 20, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_pos += 25
        
        contadores = [
            (f"Sem Copo: {self.contador_sem_copo}/10", (128, 128, 128)),
            (f"Copo Bom: {self.contador_copo_bom}/10", (0, 255, 0)),
            (f"Danificado: {self.contador_copo_danificado}/10", (0, 0, 255))
        ]
        
        for texto, cor in contadores:
            cv2.putText(frame, texto, (painel_x + 20, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, cor, 1)
            y_pos += 20
        
        # Status dos componentes
        y_pos += 20
        componentes = [
            (f"PLC: {'ON' if self.plc.conectado else 'OFF'}", 
             (0, 255, 0) if self.plc.conectado else (0, 0, 255)),
            (f"DB18: {'OK' if self.plc.db18_disponivel else 'OFF'}", 
             (0, 255, 0) if self.plc.db18_disponivel else (255, 255, 0)),
            (f"WebSocket: {self.websocket.get_client_count()} clients", (0, 255, 255))
        ]
        
        for texto, cor in componentes:
            cv2.putText(frame, texto, (painel_x + 20, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, cor, 1)
            y_pos += 20
        
        # Controles
        controles = [
            "CONTROLES:",
            "T=Treinar D=Detectar R=Reset",
            "V=SemCopo C=CopoBom S=Dano",
            "ESC=Sair"
        ]
        
        for i, controle in enumerate(controles):
            cv2.putText(frame, controle, (10, frame.shape[0] - (len(controles) - i) * 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
    
    def desenhar_barra(self, frame, x, y, largura, altura, valor, cor, label):
        """Desenhar barra de progresso"""
        # Fundo
        cv2.rectangle(frame, (x, y), (x + largura, y + altura), (50, 50, 50), -1)
        
        # Valor
        barra_largura = int(largura * min(valor, 1.0))
        if barra_largura > 0:
            cv2.rectangle(frame, (x, y), (x + barra_largura, y + altura), cor, -1)
        
        # Texto
        texto = f"{label}: {valor:.3f}"
        cv2.putText(frame, texto, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, cor, 1)
        
        # Borda
        cv2.rectangle(frame, (x, y), (x + largura, y + altura), (255, 255, 255), 1)
    
    def processar_teclado(self, key):
        """Processar comandos do teclado"""
        if key == ord('t'):
            self.modo_atual = "TREINAMENTO"
            print("📚 Modo TREINAMENTO")
        elif key == ord('d') and self.treinamento_completo:
            self.modo_atual = "DETECCAO"
            print("🎯 Modo DETECÇÃO")
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
        print("🚀 SISTEMA MODULAR INICIADO")
        print(f"🌐 WebSocket: ws://localhost:{self.websocket.port}")
        print("=" * 50)
        
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
                
                # Interface visual
                self.desenhar_interface(frame)
                
                # Definir cor da área baseada no estado
                if self.modo_atual == "DETECCAO":
                    cores = {
                        "SEM_COPO": (128, 128, 128),
                        "COPO_BOM": (0, 255, 0),
                        "COPO_DANIFICADO": (0, 0, 255)
                    }
                    cor_area = cores.get(self.estado_detectado, (255, 100, 0))
                else:
                    cor_area = (255, 100, 0)
                
                self.camera.desenhar_area(frame, cor_area)
                
                # Mostrar frame
                cv2.imshow('DETECTOR MODULAR', frame)
                
                # Processar teclado
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    break
                elif key != 255:
                    self.processar_teclado(key)
                
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
        
        # Fechar OpenCV
        cv2.destroyAllWindows()
        
        print("✅ Sistema finalizado")

def main():
    """Função principal"""
    print("🥤 DETECTOR MODULAR + PLC + WEBSOCKET")
    print("🔧 Arquitetura modular para fácil manutenção")
    print("🌐 WebSocket para integração web")
    print("=" * 50)
    
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
    
    # Executar sistema
    detector.executar()

if __name__ == "__main__":
    main()