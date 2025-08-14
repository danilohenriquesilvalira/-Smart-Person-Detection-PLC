import cv2
import numpy as np

# YOLO
try:
    from ultralytics import YOLO
    model = YOLO('yolov8n.pt')
    print("✅ YOLO carregado")
except:
    print("❌ pip install ultralytics")
    exit()

# Tracker para manter detecções
class TrackerBarco:
    def __init__(self):
        self.ultimo_barco = None
        self.frames_sem_deteccao = 0
        self.confianca_acumulada = 0
        
    def atualizar(self, barcos):
        """Mantém barco detectado por até 30 frames"""
        if barcos:
            # Tem detecção nova
            self.ultimo_barco = barcos[0]
            self.frames_sem_deteccao = 0
            self.confianca_acumulada = min(self.confianca_acumulada + 0.1, 1.0)
            return self.ultimo_barco
        else:
            # Sem detecção - usar última conhecida
            self.frames_sem_deteccao += 1
            self.confianca_acumulada = max(self.confianca_acumulada - 0.05, 0)
            
            # Manter por até 30 frames (1-2 segundos)
            if self.frames_sem_deteccao < 30 and self.ultimo_barco:
                return self.ultimo_barco
            else:
                self.ultimo_barco = None
                return None

# URL
RTSP_URL = "rtsp://DaniloLira:Danilo%4034333528@192.168.0.100:554/stream2"

def conectar():
    """Conectar câmera"""
    cap = cv2.VideoCapture(RTSP_URL)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 15)
    
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    
    return cap

def detectar_barco_melhorado(frame):
    """Detectar com múltiplas classes que podem ser barcos"""
    h, w = frame.shape[:2]
    
    # Resize para 640 se necessário
    if w > 640:
        frame_small = cv2.resize(frame, (640, 480))
        scale = w / 640
    else:
        frame_small = frame
        scale = 1
    
    # YOLO com múltiplas classes que podem ser barcos
    # boat=8, mas também testar: truck=7, bus=5, car=2 (às vezes detecta barcos como veículos)
    results = model(
        frame_small,
        conf=0.15,  # Confiança BEM baixa para pegar tudo
        classes=[8, 7, 5, 2],  # boat, truck, bus, car
        verbose=False
    )[0]
    
    barcos = []
    if results.boxes is not None:
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            classe = int(box.cls[0])
            
            # Escalar coordenadas
            if scale > 1:
                x1, y1, x2, y2 = [int(v * scale) for v in [x1, y1, x2, y2]]
            
            # Validar se é região de água/canal (meio inferior da tela)
            cy = (y1 + y2) // 2  # Centro Y
            if cy > h * 0.3:  # Só objetos na parte inferior (onde está a água)
                largura = x2 - x1
                altura = y2 - y1
                
                # Proporções típicas de barco
                if largura > altura * 0.8:  # Barcos são mais largos
                    barcos.append({
                        'bbox': (x1, y1, x2, y2),
                        'conf': conf,
                        'classe': classe
                    })
    
    return barcos

def processar_com_memoria(frame, tracker):
    """Processar com memória de detecções"""
    # Detectar
    barcos_detectados = detectar_barco_melhorado(frame)
    
    # Atualizar tracker
    barco_atual = tracker.atualizar(barcos_detectados)
    
    return barco_atual, tracker.confianca_acumulada

def desenhar_com_status(frame, barco, confianca_acumulada):
    """Desenhar com indicador de confiança"""
    h, w = frame.shape[:2]
    
    if barco:
        x1, y1, x2, y2 = barco['bbox']
        
        # Cor baseada na confiança acumulada
        if confianca_acumulada > 0.7:
            cor = (0, 255, 0)  # Verde - alta confiança
            status = "BARCO CONFIRMADO"
        elif confianca_acumulada > 0.3:
            cor = (0, 200, 255)  # Amarelo - média confiança
            status = "BARCO DETECTADO"
        else:
            cor = (0, 100, 255)  # Laranja - baixa confiança
            status = "POSSÍVEL BARCO"
        
        # Desenhar caixa
        cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 3)
        
        # Label com nome do barco se visível
        label = f"{status} [{barco['conf']:.0%}]"
        cv2.putText(frame, label, (x1, y1-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor, 2)
        
        # Barra de confiança acumulada
        bar_width = int(200 * confianca_acumulada)
        cv2.rectangle(frame, (10, 10), (210, 30), (100, 100, 100), -1)
        cv2.rectangle(frame, (10, 10), (10 + bar_width, 30), cor, -1)
        cv2.putText(frame, f"Confianca: {confianca_acumulada:.0%}", 
                   (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    else:
        cv2.putText(frame, "PROCURANDO BARCOS...", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Área de detecção (onde esperamos barcos)
    cv2.rectangle(frame, (0, int(h*0.3)), (w, h), (255, 255, 0), 1)
    cv2.putText(frame, "ZONA DE DETECCAO", (10, int(h*0.3)+20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    
    return frame

def main():
    """Sistema com tracking persistente"""
    print("🚢 DETECTOR COM MEMÓRIA")
    print("=" * 40)
    print("✅ Mantém detecção por 30 frames")
    print("✅ Acumula confiança ao longo do tempo")
    print("✅ Zona de detecção definida")
    print("=" * 40)
    
    cap = conectar()
    tracker = TrackerBarco()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        
        # Processar com memória
        barco, confianca = processar_com_memoria(frame, tracker)
        
        # Desenhar
        frame = desenhar_com_status(frame, barco, confianca)
        
        # Log quando detecta com alta confiança
        if barco and confianca > 0.7:
            print(f"🚢 BARCO CONFIRMADO! Confiança: {confianca:.0%}")
        
        cv2.imshow("DETECTOR PERSISTENTE", frame)
        
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()