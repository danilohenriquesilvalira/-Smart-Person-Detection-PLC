"""
🔧 Serviço de Câmera - Smart Detection Backend
"""
import cv2
import numpy as np
import time
import threading
from typing import Optional, Tuple, Callable
from pathlib import Path

from config.settings import CAMERA_CONFIG
from ..utils.image_utils import extract_roi_from_frame

class CameraService:
    """📷 Serviço gerenciador de câmera"""
    
    def __init__(self, rtsp_url: str = None):
        self.rtsp_url = rtsp_url or CAMERA_CONFIG["rtsp_url"]
        self.buffer_size = CAMERA_CONFIG["buffer_size"]
        self.area_size = CAMERA_CONFIG["area_size"]
        self.image_size = CAMERA_CONFIG["image_size"]
        
        # Estado da câmera
        self.cap = None
        self.is_connected = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # ROI (Região de interesse)
        self.roi_coords = None
        
        # Streaming
        self.is_streaming = False
        self.frame_callbacks = []
        
        print(f"📷 Serviço de câmera inicializado: {self.rtsp_url}")
    
    def connect(self) -> bool:
        """🔗 Conectar à câmera"""
        try:
            print(f"📷 Conectando à câmera...")
            self.cap = cv2.VideoCapture(self.rtsp_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
            
            if not self.cap.isOpened():
                print(f"❌ Falha ao abrir câmera: {self.rtsp_url}")
                return False
            
            # Testar leitura de frame
            ret, test_frame = self.cap.read()
            if not ret:
                print("❌ Falha ao ler frame inicial")
                self.disconnect()
                return False
            
            # Definir ROI baseado no primeiro frame
            self._setup_roi(test_frame)
            
            self.is_connected = True
            print("✅ Câmera conectada com sucesso")
            
            # Iniciar thread de captura
            self._start_capture_thread()
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao conectar câmera: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """🔌 Desconectar câmera"""
        self.is_connected = False
        self.is_streaming = False
        
        if self.cap:
            try:
                self.cap.release()
                print("📷 Câmera desconectada")
            except Exception as e:
                print(f"⚠️ Erro ao desconectar câmera: {e}")
            finally:
                self.cap = None
        
        with self.frame_lock:
            self.current_frame = None
    
    def _setup_roi(self, frame: np.ndarray):
        """🎯 Configurar região de interesse (ROI)"""
        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        half_size = self.area_size // 2
        
        self.roi_coords = (
            center_x - half_size,
            center_y - half_size,
            center_x + half_size,
            center_y + half_size
        )
        
        print(f"🎯 ROI definida: {self.roi_coords}")
    
    def _start_capture_thread(self):
        """🔄 Iniciar thread de captura de frames"""
        capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        capture_thread.name = "CameraCapture"
        capture_thread.start()
        print("🔄 Thread de captura iniciada")
    
    def _capture_loop(self):
        """🔄 Loop principal de captura"""
        reconnect_attempts = 0
        max_reconnect_attempts = 5
        
        while self.is_connected:
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    print("⚠️ Falha ao capturar frame")
                    reconnect_attempts += 1
                    
                    if reconnect_attempts >= max_reconnect_attempts:
                        print("❌ Máximo de tentativas de reconexão atingido")
                        self.is_connected = False
                        break
                    
                    # Tentar reconectar
                    time.sleep(1)
                    self._attempt_reconnect()
                    continue
                
                # Reset contador de reconexão
                reconnect_attempts = 0
                
                # Atualizar frame atual
                with self.frame_lock:
                    self.current_frame = frame.copy()
                
                # Chamar callbacks de frame
                for callback in self.frame_callbacks:
                    try:
                        callback(frame.copy())
                    except Exception as e:
                        print(f"⚠️ Erro em callback de frame: {e}")
                
                time.sleep(0.01)  # Pequeno delay para não sobrecarregar
                
            except Exception as e:
                print(f"❌ Erro no loop de captura: {e}")
                time.sleep(1)
    
    def _attempt_reconnect(self):
        """🔄 Tentar reconectar câmera"""
        print("🔄 Tentando reconectar câmera...")
        
        try:
            if self.cap:
                self.cap.release()
            
            self.cap = cv2.VideoCapture(self.rtsp_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
            
            if self.cap.isOpened():
                print("✅ Câmera reconectada")
            else:
                print("❌ Falha na reconexão")
                
        except Exception as e:
            print(f"❌ Erro na reconexão: {e}")
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """📸 Obter frame atual"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            else:
                # Retornar frame de placeholder se não houver frame
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(placeholder, 'Camera Disconnected', (200, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                return placeholder
    
    def get_roi_from_current_frame(self) -> Optional[np.ndarray]:
        """🎯 Extrair ROI do frame atual"""
        frame = self.get_current_frame()
        
        if frame is None or self.roi_coords is None:
            return None
        
        return extract_roi_from_frame(frame, self.roi_coords)
    
    def draw_roi_on_frame(self, frame: np.ndarray, color: Tuple[int, int, int] = (0, 255, 255)) -> np.ndarray:
        """🖊️ Desenhar ROI no frame"""
        if self.roi_coords is None:
            return frame
        
        x1, y1, x2, y2 = self.roi_coords
        frame_with_roi = frame.copy()
        
        # Garantir que frame está em cor (BGR)
        if len(frame_with_roi.shape) == 2:
            frame_with_roi = cv2.cvtColor(frame_with_roi, cv2.COLOR_GRAY2BGR)
        elif len(frame_with_roi.shape) == 3 and frame_with_roi.shape[2] == 4:
            frame_with_roi = cv2.cvtColor(frame_with_roi, cv2.COLOR_BGRA2BGR)
        
        # Desenhar retângulo amarelo (BGR format)
        cv2.rectangle(frame_with_roi, (x1, y1), (x2, y2), color, 3)
        
        # Desenhar cruz no centro
        center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.line(frame_with_roi, (center_x - 20, center_y), (center_x + 20, center_y), color, 2)
        cv2.line(frame_with_roi, (center_x, center_y - 20), (center_x, center_y + 20), color, 2)
        
        return frame_with_roi
    
    def add_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """➕ Adicionar callback para novos frames"""
        self.frame_callbacks.append(callback)
    
    def remove_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """➖ Remover callback de frame"""
        if callback in self.frame_callbacks:
            self.frame_callbacks.remove(callback)
    
    def start_streaming(self) -> bool:
        """▶️ Iniciar streaming"""
        if not self.is_connected:
            return False
        
        self.is_streaming = True
        print("▶️ Streaming iniciado")
        return True
    
    def stop_streaming(self):
        """⏹️ Parar streaming"""
        self.is_streaming = False
        print("⏹️ Streaming parado")
    
    def capture_roi_image(self) -> Optional[np.ndarray]:
        """📸 Capturar imagem da ROI para treinamento"""
        roi = self.get_roi_from_current_frame()
        
        if roi is None:
            return None
        
        # Redimensionar para tamanho de treinamento
        if len(roi.shape) == 3:
            roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        return cv2.resize(roi, self.image_size)
    
    def get_status(self) -> dict:
        """📊 Obter status da câmera"""
        return {
            "connected": self.is_connected,
            "streaming": self.is_streaming,
            "rtsp_url": self.rtsp_url,
            "roi_defined": self.roi_coords is not None,
            "current_frame_available": self.current_frame is not None,
            "roi_coords": self.roi_coords
        }
    
    def __del__(self):
        """🧹 Limpeza na destruição"""
        self.disconnect()

# 🏭 Instância global do serviço de câmera
camera_service = CameraService()