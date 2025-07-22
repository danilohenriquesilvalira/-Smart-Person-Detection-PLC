"""
⚙️ Configurações Centralizadas - Smart Detection Backend
"""
import os
from pathlib import Path

# 📂 Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
TRAINING_DATA_DIR = DATA_DIR / "training"

# 📷 CONFIGURAÇÕES DA CÂMERA
CAMERA_CONFIG = {
    "rtsp_url": "rtsp://DaniloLira:Danilo%4034333528@192.168.0.100:554/stream2",
    "buffer_size": 1,
    "area_size": 200,  # Tamanho da área de detecção (pixels)
    "image_size": (100, 100)  # Tamanho das imagens de treinamento
}

# 🔌 CONFIGURAÇÕES DO PLC
PLC_CONFIG = {
    "ip": "192.168.0.33",
    "rack": 0,
    "slot": 1,
    "db17_number": 17,  # DB original para compatibilidade
    "db18_number": 18,  # DB nova interface simples
    "timeout": 5.0
}

# 🌐 CONFIGURAÇÕES DO WEBSOCKET
WEBSOCKET_CONFIG = {
    "host": "localhost",
    "port": 8765,
    "max_clients": 10
}

# 🎯 CONFIGURAÇÕES DE TREINAMENTO
TRAINING_CONFIG = {
    "max_photos_per_class": 10,
    "data_folder": str(TRAINING_DATA_DIR),
    "classes": ["sem_copo", "copo_bom", "copo_danificado"],
    "image_extensions": [".jpg", ".jpeg", ".png"]
}

# 🔍 CONFIGURAÇÕES DE DETECÇÃO
DETECTION_CONFIG = {
    "default_sensitivity": 0.1,
    "min_sensitivity": 0.01,
    "max_sensitivity": 0.5,
    "stability_history_size": 3,
    "stability_threshold": 2,  # Mínimo de ocorrências para aceitar mudança
    "min_capture_interval": 1.0  # Segundos entre capturas
}

# 🎨 CONFIGURAÇÕES DE INTERFACE
INTERFACE_CONFIG = {
    "panel_width": 400,
    "panel_height": 550,
    "panel_transparency": 0.7,
    "colors": {
        "sem_copo": (128, 128, 128),
        "copo_bom": (0, 255, 0),
        "copo_danificado": (0, 0, 255),
        "aguardando": (255, 255, 0),
        "treinamento": (0, 255, 255),
        "area_deteccao": (255, 100, 0),
        "texto": (255, 255, 255),
        "painel_fundo": (0, 0, 0)
    }
}

# 📡 CONFIGURAÇÕES DE COMUNICAÇÃO
COMMUNICATION_CONFIG = {
    "plc_update_interval": 3,  # Atualizar PLC a cada N frames
    "websocket_update_interval": 6,  # Atualizar WebSocket a cada N frames
    "frame_rate": 30  # FPS alvo
}

# 📝 CONFIGURAÇÕES DE LOG
LOG_CONFIG = {
    "enable_logging": True,
    "log_level": "INFO",
    "log_file": "detector.log",
    "max_log_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5
}

# 🌐 CONFIGURAÇÕES DA API REST
API_CONFIG = {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": False,
    "cors_enabled": True,
    "max_content_length": 16 * 1024 * 1024,  # 16MB
    "upload_folder": str(TRAINING_DATA_DIR)
}

# 💬 MENSAGENS DO SISTEMA
MESSAGES = {
    "startup": "🥤 SMART DETECTION SYSTEM INICIADO",
    "camera_ok": "📷 Câmera conectada",
    "camera_fail": "❌ Falha na câmera",
    "plc_ok": "🔌 PLC conectado",
    "plc_fail": "❌ PLC desconectado",
    "websocket_ok": "🌐 WebSocket ativo",
    "api_ok": "🌐 API REST ativa",
    "training_complete": "🎉 TREINAMENTO COMPLETO!",
    "system_reset": "🔄 Sistema resetado",
    "shutdown": "🛑 Sistema finalizado"
}

# ⌨️ TECLAS DE CONTROLE
KEYBOARD_CONTROLS = {
    27: "exit",          # ESC
    ord('t'): "train",   # T
    ord('d'): "detect",  # D
    ord('r'): "reset",   # R
    ord('v'): "capture_empty",    # V
    ord('c'): "capture_good",     # C
    ord('s'): "capture_damaged"   # S
}

def ensure_directories():
    """🗂️ Garantir que as pastas necessárias existam"""
    directories = [
        DATA_DIR,
        TRAINING_DATA_DIR,
        TRAINING_DATA_DIR / "sem_copo",
        TRAINING_DATA_DIR / "copo_bom", 
        TRAINING_DATA_DIR / "copo_danificado"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    
    print(f"✅ Estrutura de pastas criada em: {TRAINING_DATA_DIR}")

def validate_config():
    """✅ Validar configurações básicas"""
    errors = []
    
    # Validar sensibilidade
    sens = DETECTION_CONFIG["default_sensitivity"]
    if not (DETECTION_CONFIG["min_sensitivity"] <= sens <= DETECTION_CONFIG["max_sensitivity"]):
        errors.append("Sensibilidade padrão fora dos limites")
    
    # Validar porta WebSocket
    ws_port = WEBSOCKET_CONFIG["port"]
    if not (1024 <= ws_port <= 65535):
        errors.append("Porta WebSocket inválida")
    
    # Validar porta API
    api_port = API_CONFIG["port"] 
    if not (1024 <= api_port <= 65535):
        errors.append("Porta API inválida")
    
    # Validar tamanho da área
    area_size = CAMERA_CONFIG["area_size"]
    if area_size < 50 or area_size > 500:
        errors.append("Tamanho da área de detecção inválido")
    
    if errors:
        print("❌ Erros de configuração:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    return True

def get_training_paths():
    """📁 Retornar caminhos das pastas de treinamento"""
    return {
        "sem_copo": TRAINING_DATA_DIR / "sem_copo",
        "copo_bom": TRAINING_DATA_DIR / "copo_bom",
        "copo_danificado": TRAINING_DATA_DIR / "copo_danificado"
    }

# 🚀 Inicialização automática
if __name__ == "__main__":
    ensure_directories()
    if validate_config():
        print("✅ Configurações válidas")
        print(f"📂 Pasta de treinamento: {TRAINING_DATA_DIR}")
    else:
        print("❌ Configurações inválidas")
else:
    # Garantir pastas na importação
    ensure_directories()