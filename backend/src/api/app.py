"""
🌐 Flask Application - Smart Detection API
"""
import os
from flask import Flask, jsonify, Response, request
from flask_cors import CORS
from waitress import serve
import threading
import time

# Configurações
from config.settings import API_CONFIG, WEBSOCKET_CONFIG, MESSAGES

# Serviços  
from ..services.camera_service import camera_service

# Rotas
from .routes.training_routes import training_bp

class SmartDetectionAPI:
    """🌐 Aplicação principal da API"""
    
    def __init__(self):
        self.app = self._create_app()
        self.server_thread = None
        self.is_running = False
        
        # Registrar rotas
        self._register_routes()
        
        print("🌐 API Smart Detection inicializada")
    
    def _create_app(self) -> Flask:
        """🏭 Criar aplicação Flask"""
        # Suprimir logs do Werkzeug
        os.environ['WERKZEUG_RUN_MAIN'] = 'true'
        
        app = Flask(__name__)
        
        # Configurações
        app.config['MAX_CONTENT_LENGTH'] = API_CONFIG["max_content_length"]
        app.config['UPLOAD_FOLDER'] = API_CONFIG["upload_folder"]
        
        # CORS
        if API_CONFIG["cors_enabled"]:
            CORS(app)
        
        # Suprimir logs desnecessários
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        return app
    
    def _register_routes(self):
        """🛣️ Registrar todas as rotas"""
        
        # Registrar blueprints
        self.app.register_blueprint(training_bp)
        
        # Rota principal
        @self.app.route('/')
        def index():
            return jsonify({
                "service": "Smart Detection API",
                "version": "1.0.0",
                "status": "active",
                "endpoints": {
                    "training": "/api/training/*",
                    "video_feed": "/video_feed",
                    "system": "/api/system/*"
                }
            })
        
        # Rota de saúde
        @self.app.route('/health')
        def health_check():
            return jsonify({
                "status": "healthy",
                "timestamp": time.time(),
                "services": {
                    "api": True,
                    "camera": camera_service.is_connected,
                    "websocket": True  # Será atualizado quando integrarmos
                }
            })
        
        # Streaming de vídeo
        @self.app.route('/video_feed')
        def video_feed():
            return Response(
                self._generate_video_stream(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
        
        # Rota de sistema
        @self.app.route('/api/system/status')
        def system_status():
            camera_status = camera_service.get_status()
            
            return jsonify({
                "success": True,
                "data": {
                    "camera": camera_status,
                    "api": {
                        "running": self.is_running,
                        "host": API_CONFIG["host"],
                        "port": API_CONFIG["port"]
                    },
                    "websocket": {
                        "host": WEBSOCKET_CONFIG["host"],
                        "port": WEBSOCKET_CONFIG["port"]
                    }
                }
            })
        
        # Controles da câmera
        @self.app.route('/api/camera/connect', methods=['POST'])
        def camera_connect():
            success = camera_service.connect()
            
            return jsonify({
                "success": success,
                "message": "Câmera conectada" if success else "Falha ao conectar câmera",
                "status": camera_service.get_status()
            })
        
        @self.app.route('/api/camera/disconnect', methods=['POST'])
        def camera_disconnect():
            camera_service.disconnect()
            
            return jsonify({
                "success": True,
                "message": "Câmera desconectada",
                "status": camera_service.get_status()
            })
        
        @self.app.route('/api/camera/status', methods=['GET'])
        def camera_status():
            return jsonify({
                "success": True,
                "data": camera_service.get_status()
            })
        
        # Handler de erro
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                "success": False,
                "error": "Endpoint não encontrado",
                "available_endpoints": [
                    "/",
                    "/health",
                    "/video_feed",
                    "/api/training/*",
                    "/api/system/status",
                    "/api/camera/*"
                ]
            }), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({
                "success": False,
                "error": "Erro interno do servidor"
            }), 500
    
    def _generate_video_stream(self):
        """📹 Gerar stream de vídeo"""
        import cv2
        
        while camera_service.is_connected:
            try:
                frame = camera_service.get_current_frame()
                
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # Desenhar ROI
                frame_with_roi = camera_service.draw_roi_on_frame(frame, color=(0, 255, 255))
                
                # Codificar frame
                ret, buffer = cv2.imencode('.jpg', frame_with_roi, 
                                         [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                
                if not ret:
                    time.sleep(0.1)
                    continue
                
                frame_bytes = buffer.tobytes()
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                time.sleep(0.03)  # ~30 FPS
                
            except Exception as e:
                print(f"❌ Erro no stream de vídeo: {e}")
                time.sleep(0.5)
    
    def start_server(self) -> bool:
        """🚀 Iniciar servidor da API"""
        try:
            def run_server():
                serve(
                    self.app,
                    host=API_CONFIG["host"],
                    port=API_CONFIG["port"],
                    threads=4
                )
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.name = "API-Server"
            self.server_thread.start()
            
            self.is_running = True
            
            print(f"🚀 {MESSAGES['api_ok']}")
            print(f"🌐 API URL: http://{API_CONFIG['host']}:{API_CONFIG['port']}")
            print(f"📹 Video Stream: http://{API_CONFIG['host']}:{API_CONFIG['port']}/video_feed")
            print(f"🖼️ Training Images: http://{API_CONFIG['host']}:{API_CONFIG['port']}/api/training/images")
            
            time.sleep(1)  # Aguardar inicialização
            return True
            
        except Exception as e:
            print(f"❌ Erro ao iniciar servidor API: {e}")
            self.is_running = False
            return False
    
    def stop_server(self):
        """🛑 Parar servidor da API"""
        self.is_running = False
        print("🛑 Servidor API finalizado")
    
    def get_app(self) -> Flask:
        """📱 Obter instância da aplicação Flask"""
        return self.app

# 🏭 Instância global da API
api_app = SmartDetectionAPI()

def create_app() -> Flask:
    """🏭 Factory function para criar app Flask"""
    return api_app.get_app()

# 🧪 Para execução direta
if __name__ == "__main__":
    print("🧪 Executando API em modo de desenvolvimento")
    
    # Conectar câmera
    if camera_service.connect():
        print("✅ Câmera conectada")
    else:
        print("⚠️ Câmera não conectada - API funcionará sem streaming")
    
    # Iniciar servidor
    if api_app.start_server():
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Finalizando API...")
            api_app.stop_server()
            camera_service.disconnect()
    else:
        print("❌ Falha ao iniciar API")