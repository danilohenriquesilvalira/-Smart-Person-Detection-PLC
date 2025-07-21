# video_stream_standalone.py

# --- A PRIMEIRÍSSIMA LINHA EXECUTÁVEL DO SCRIPT ---
import os
os.environ['WERKZEUG_RUN_MAIN'] = 'true'
# --------------------------------------------------

import cv2
from flask import Flask, Response
from flask_cors import CORS
import threading
import time
import numpy as np # Necessário para operações com arrays do OpenCV
from waitress import serve

# --- Configuração da Aplicação Flask ---
app = Flask(__name__)
CORS(app)

# --- Variáveis Globais para Gerenciamento da Câmera e ROI ---
camera_capture = None
current_frame = None
is_camera_running = False
frame_lock = threading.Lock()
_camera_source_global = None

# Variáveis para a ROI (Região de Interesse)
area_coords = None # (x1, y1, x2, y2)
tamanho_area = 200 # Tamanho do lado da área quadrada em pixels

# --- Funções de Gerenciamento da Câmera ---
def start_camera(camera_source_param=0):
    global camera_capture, is_camera_running, current_frame, _camera_source_global
    
    _camera_source_global = camera_source_param
    
    print(f"Tentando iniciar câmera/fonte: {_camera_source_global}...")
    camera_capture = cv2.VideoCapture(_camera_source_global)
    
    # Adicionando set CAP_PROP_BUFFERSIZE para reduzir latência
    # O valor 1 minimiza o buffer, o que é bom para streams em tempo real.
    camera_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1) 
    
    if not camera_capture.isOpened():
        print(f"ERRO: Não foi possível abrir a câmera/fonte: {_camera_source_global}")
        is_camera_running = False
        return False
    
    is_camera_running = True
    print(f"Câmera/fonte {_camera_source_global} aberta com sucesso.")
    
    read_thread = threading.Thread(target=_read_frames_loop)
    read_thread.daemon = True 
    read_thread.start()
    return True

def _read_frames_loop():
    global current_frame, is_camera_running, camera_capture, _camera_source_global
    
    while is_camera_running:
        ret, frame = camera_capture.read()
        if not ret:
            print("AVISO: Falha ao ler frame da câmera. Tentando novamente...")
            if not camera_capture.isOpened():
                print("Câmera parece estar desconectada, tentando reconectar...")
                camera_capture.release()
                time.sleep(1)
                camera_capture = cv2.VideoCapture(_camera_source_global)
                # Tenta redefinir o buffer após reconexão
                if camera_capture.isOpened():
                    camera_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if not camera_capture.isOpened():
                    print("Falha ao reconectar a câmera. Continuar tentando...")
                    time.sleep(0.5)
                    continue
                else:
                    print("Câmera reconectada com sucesso.")
            else:
                time.sleep(0.05)
            continue

        with frame_lock:
            current_frame = frame.copy()
        time.sleep(0.01)

def get_current_frame_standalone():
    with frame_lock:
        return current_frame.copy() if current_frame is not None else None

def stop_camera():
    global is_camera_running
    is_camera_running = False
    if camera_capture:
        camera_capture.release()
        print("Câmera/fonte liberada.")

# --- Funções para a ROI (Adaptadas do seu CameraManager) ---
def definir_area_roi(frame):
    """Define a área central de detecção (ROI) com base no tamanho do frame."""
    global area_coords, tamanho_area
    if frame is None:
        return

    h, w = frame.shape[:2]
    centro_x, centro_y = w // 2, h // 2
    meio = tamanho_area // 2
    area_coords = (centro_x - meio, centro_y - meio, centro_x + meio, centro_y + meio)
    print(f"ROI definida: {area_coords}")

def desenhar_area_roi(frame, cor=(255, 100, 0)):
    """Desenha o retângulo da ROI e o ponto central no frame."""
    global area_coords
    if area_coords is None:
        return
    
    x1, y1, x2, y2 = area_coords
    cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 3)
    
    centro_x, centro_y = (x1 + x2) // 2, (y1 + y2) // 2
    cv2.line(frame, (centro_x - 20, centro_y), (centro_x + 20, centro_y), cor, 2)
    cv2.line(frame, (centro_x, centro_y - 20), (centro_x, centro_y + 20), cor, 2)

# --- Funções do Flask para Stream MJPEG ---
@app.route('/video_feed')
def video_feed_standalone():
    print("Requisição recebida para /video_feed")
    return Response(generate_mjpeg_frames_standalone(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_mjpeg_frames_standalone():
    """
    Função geradora que continuamente busca frames da câmera, desenha a ROI,
    e os envia como stream MJPEG.
    """
    global area_coords # Usar para verificar se a ROI já foi definida
    
    while True:
        frame = get_current_frame_standalone()
        if frame is None:
            time.sleep(0.1)
            continue

        # Se a ROI ainda não foi definida, define-a com base no primeiro frame válido
        if area_coords is None:
            definir_area_roi(frame)
        
        try:
            # Desenha a área de detecção (ROI) no frame
            desenhar_area_roi(frame, cor=(0, 255, 255)) # Cor amarela para visibilidade

            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret:
                print("ERRO: Falha ao codificar frame para JPEG.")
                time.sleep(0.1)
                continue

            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            time.sleep(0.03)

        except Exception as e:
            print(f"ERRO INESPERADO no generate_mjpeg_frames_standalone: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(1)

# --- Função Principal para Execução Autônoma do Script ---
if __name__ == '__main__':
    # --- CONFIGURE AQUI A FONTE DA SUA CÂMERA ---
    camera_source = "rtsp://DaniloLira:Danilo%4034333528@192.168.0.100:554/stream2" # <-- SUA URL RTSP

    if not start_camera(camera_source):
        print("Não foi possível iniciar a câmera. O script será encerrado.")
        exit(1)

    print(f"Waitress (Flask) Video Stream Standalone iniciado em http://0.0.0.0:5000/video_feed")
    try:
        serve(app, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\nServidor Waitress (Flask) interrompido pelo usuário.")
    except Exception as e:
        print(f"\nErro inesperado ao iniciar o servidor Waitress (Flask): {e}")
        import traceback
        traceback.print_exc()
    finally:
        stop_camera()
        print("Script finalizado.")