"""
🔧 HMI Service - SÓ O BÁSICO QUE FUNCIONA
"""
import threading
import time
from flask import Flask, send_file
from waitress import serve
import os
import cv2
import numpy as np
from io import BytesIO

from ..services.camera_service import camera_service

class HMIService:
    
    def __init__(self):
        self.app = self._create_app()
        self.server_thread = None
        self.is_running = False
        self.hmi_port = 8080
        
        print("📺 HMI básico inicializado")
    
    def _create_app(self) -> Flask:
        os.environ['WERKZEUG_RUN_MAIN'] = 'true'
        app = Flask(__name__)
        
        import logging
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        logging.getLogger('waitress').setLevel(logging.ERROR)
        
        # SÓ 2 ROTAS
        @app.route('/')
        def pagina_hmi():
            # Use a regular triple-quoted string for HTML and JavaScript
            # The JavaScript will handle refreshing the image on the frontend
            html_content = '''
<html>
<head>
    <title>HMI Camera Feed</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f0f0f0;">
    <img id="cameraFeed" src="/foto?t=''' + str(int(time.time() * 1000)) + '''" alt="Camera Feed">
    <script>
        // Function to refresh the image
        function refreshImage() {
            const img = document.getElementById('cameraFeed');
            if (img) {
                // Append a unique timestamp to bypass browser cache
                img.src = '/foto?t=' + new Date().getTime();
            }
        }

        // Set the image to refresh immediately after loading
        document.getElementById('cameraFeed').onload = function() {
            setTimeout(refreshImage, 50); // Refresh every 50 milliseconds (adjust for desired speed)
        };
        // Initial load error handling for first image
        document.getElementById('cameraFeed').onerror = function() {
            // If the first load fails, try again after a short delay
            setTimeout(refreshImage, 500); 
        };
    </script>
</body>
</html>
            '''
            return html_content
        
        @app.route('/foto')
        def foto():
            try:
                if camera_service.is_connected:
                    frame = camera_service.get_current_frame()
                    if frame is not None:
                        # Ensure the frame has a 16:9 aspect ratio before sending.
                        # Common resolutions for 16:9: 640x360, 854x480, 1280x720 (HD)
                        # Let's target a resolution that matches 16:9 aspect, e.g., 640x360
                        target_width = 640
                        target_height = 360 # 640 * (9/16) = 360

                        h, w, _ = frame.shape
                        
                        # Calculate current aspect ratio
                        current_aspect_ratio = w / h
                        
                        # Calculate target aspect ratio
                        target_aspect_ratio = target_width / target_height

                        # Adjust frame to fit 16:9 aspect ratio (crop if necessary)
                        if current_aspect_ratio > target_aspect_ratio: # Frame is wider than 16:9
                            new_w = int(h * target_aspect_ratio)
                            start_x = (w - new_w) // 2
                            frame = frame[:, start_x : start_x + new_w]
                        elif current_aspect_ratio < target_aspect_ratio: # Frame is taller than 16:9
                            new_h = int(w / target_aspect_ratio)
                            start_y = (h - new_h) // 2
                            frame = frame[start_y : start_y + new_h, :]
                        
                        # Now resize to the target 16:9 resolution
                        resized_frame = cv2.resize(frame, (target_width, target_height))
                        
                        frame_roi = camera_service.draw_roi_on_frame(resized_frame, color=(0, 255, 255))
                        
                        ret, buffer = cv2.imencode('.jpg', frame_roi, 
                                                     [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                        if ret:
                            response = send_file(BytesIO(buffer), mimetype='image/jpeg')
                            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                            response.headers['Pragma'] = 'no-cache'
                            response.headers['Expires'] = '0'
                            return response
                
                # Placeholder for when camera is not connected or frame is None
                placeholder_width = 640
                placeholder_height = 360
                img = np.zeros((placeholder_height, placeholder_width, 3), dtype=np.uint8)
                img[:] = (40, 40, 100) # Dark blueish background
                
                text = 'SEM CAMERA'
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 1.0
                font_thickness = 2
                text_size = cv2.getTextSize(text, font, font_scale, font_thickness)[0]
                text_x = (placeholder_width - text_size[0]) // 2
                text_y = (placeholder_height + text_size[1]) // 2
                cv2.putText(img, text, (text_x, text_y), 
                            font, font_scale, (0, 0, 255), font_thickness) # Red text
                
                ret, buffer = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
                response = send_file(BytesIO(buffer), mimetype='image/jpeg')
                response.headers['Cache-Control'] = 'no-cache'
                return response
                
            except Exception as e:
                print(f"Erro ao gerar foto: {e}") 
                error_width = 640
                error_height = 360
                erro = np.zeros((error_height, error_width, 3), dtype=np.uint8)
                erro[:] = (100, 0, 0) # Dark red background
                
                text = 'ERRO'
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 1.0
                font_thickness = 2
                text_size = cv2.getTextSize(text, font, font_scale, font_thickness)[0]
                text_x = (error_width - text_size[0]) // 2
                text_y = (error_height + text_size[1]) // 2
                cv2.putText(erro, text, (text_x, text_y), 
                            font, font_scale, (0, 0, 255), font_thickness) # Red text
                
                ret, buffer = cv2.imencode('.jpg', erro)
                return send_file(BytesIO(buffer), mimetype='image/jpeg')
        
        return app
    
    def start_server(self) -> bool:
        try:
            def run():
                serve(self.app, host='0.0.0.0', port=self.hmi_port, threads=1)
            
            self.server_thread = threading.Thread(target=run, daemon=True)
            self.server_thread.start()
            self.is_running = True
            
            print(f"🚀 HMI: http://localhost:{self.hmi_port}")
            return True
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            return False
    
    def stop_server(self):
        self.is_running = False
    
    def get_status(self) -> dict:
        return {
            "running": self.is_running,
            "port": self.hmi_port,
            "url": f"http://localhost:{self.hmi_port}"
        }

hmi_service = HMIService()