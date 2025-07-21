import cv2
import numpy as np
import time
import os

class CameraManager:
    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.cap = None
        self.area_coords = None
        self.tamanho_area = 200
        self.frame_atual = None
        
    def conectar(self):
        """Conectar à câmera"""
        self.cap = cv2.VideoCapture(self.rtsp_url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return self.cap.isOpened()
    
    def ler_frame(self):
        """Ler frame da câmera"""
        if not self.cap:
            return False, None
        
        ret, frame = self.cap.read()
        if ret:
            self.frame_atual = frame
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
        """Desenhar área de detecção no frame"""
        if self.area_coords is None:
            return
        
        x1, y1, x2, y2 = self.area_coords
        cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 3)
        
        centro_x, centro_y = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.line(frame, (centro_x - 20, centro_y), (centro_x + 20, centro_y), cor, 2)
        cv2.line(frame, (centro_x, centro_y - 20), (centro_x, centro_y + 20), cor, 2)
    
    def desconectar(self):
        """Desconectar câmera"""
        if self.cap:
            self.cap.release()
            self.cap = None