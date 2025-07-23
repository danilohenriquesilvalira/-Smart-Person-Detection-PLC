"""
🚀 Smart Detection System - Entry Point (COM HMI)
Sistema Modular de Detecção Inteligente com PLC, API e HMI
"""
import sys
import time
import signal
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Imports dos serviços
from src.core.detector import smart_detector
from src.api.app import api_app
from src.services.hmi_service import hmi_service
from config.settings import validate_config, ensure_directories, MESSAGES

class SmartDetectionSystem:
    """🎯 Sistema Principal de Detecção Inteligente (COM HMI)"""
    
    def __init__(self):
        self.is_running = False
        self.services_started = []
        
        # Configurar handlers de sinal
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("=" * 60)
        print(MESSAGES["startup"])
        print("=" * 60)
    
    def _signal_handler(self, signum, frame):
        """🛑 Handler para sinais de interrupção"""
        print(f"\n🛑 Sinal recebido ({signum}). Finalizando sistema...")
        self.shutdown()
        sys.exit(0)
    
    def initialize(self) -> bool:
        """🚀 Inicializar sistema completo"""
        print("🚀 Inicializando Smart Detection System...")
        
        # 1. Validar configurações
        if not validate_config():
            print("❌ Configurações inválidas")
            return False
        print("✅ Configurações validadas")
        
        # 2. Garantir estrutura de diretórios
        ensure_directories()
        print("✅ Estrutura de diretórios criada")
        
        # 3. Inicializar detector principal (inclui câmera, PLC, WebSocket)
        if not smart_detector.initialize_system():
            print("❌ Falha ao inicializar detector principal")
            return False
        print("✅ Detector principal inicializado")
        self.services_started.append("detector")
        
        # 4. Inicializar API REST
        if api_app.start_server():
            print("✅ API REST inicializada")
            self.services_started.append("api")
        else:
            print("⚠️ Falha ao inicializar API REST - continuando sem API")
        
        # 5. Inicializar HMI Service (NOVO)
        if hmi_service.start_server():
            print("✅ HMI Service inicializado")
            self.services_started.append("hmi")
        else:
            print("⚠️ Falha ao inicializar HMI Service - continuando sem HMI")
        
        print("🎉 Sistema inicializado com sucesso!")
        print(self._get_system_info())
        
        return True
    
    def start(self) -> bool:
        """▶️ Iniciar sistema completo"""
        if not self.initialize():
            return False
        
        # Iniciar loop principal de detecção
        smart_detector.start_detection_loop()
        self.is_running = True
        
        print("▶️ Sistema Smart Detection ativo!")
        print("\n" + "="*60)
        print("💡 CONTROLES DISPONÍVEIS:")
        print("   🌐 Dashboard Web: Controles via navegador")
        print("   📺 HMI TP1500: Interface industrial otimizada")
        print("   🔌 PLC: Comandos via sistema industrial")
        print("   ⌨️  Teclado: ESC para sair")
        print("="*60)
        
        return True
    
    def run(self):
        """🔄 Executar loop principal"""
        if not self.start():
            print("❌ Falha ao inicializar sistema")
            return
        
        try:
            # Loop principal - manter sistema ativo
            while self.is_running:
                time.sleep(1)
                
                # Verificar saúde dos serviços periodicamente
                if int(time.time()) % 30 == 0:  # A cada 30 segundos
                    self._health_check()
            
        except KeyboardInterrupt:
            print("\n🛑 Interrupção manual detectada")
        except Exception as e:
            print(f"❌ Erro crítico no sistema: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """🛑 Finalizar sistema graciosamente"""
        if not self.is_running:
            return
        
        print("\n🛑 Finalizando Smart Detection System...")
        self.is_running = False
        
        # Finalizar serviços na ordem inversa
        if "hmi" in self.services_started:
            hmi_service.stop_server()
            print("🛑 HMI Service finalizado")
        
        if "api" in self.services_started:
            api_app.stop_server()
            print("🛑 API REST finalizada")
        
        if "detector" in self.services_started:
            smart_detector.shutdown()
            print("🛑 Detector principal finalizado")
        
        print("✅ Sistema finalizado com sucesso")
        print(MESSAGES["shutdown"])
    
    def _health_check(self):
        """💓 Verificação de saúde dos serviços"""
        try:
            status = smart_detector.get_system_status()
            
            # Log de status simplificado
            components = []
            if status["system_data"]["plc"]["conectado"]:
                components.append("PLC")
            if status["system_data"]["valores"]:
                components.append("Camera")
            if status["running"]:
                components.append("AI")
            if "hmi" in self.services_started:
                components.append("HMI")
            
            if components:
                print(f"💓 Sistema ativo - Componentes: {', '.join(components)}")
            
        except Exception as e:
            print(f"⚠️ Erro na verificação de saúde: {e}")
    
    def _get_system_info(self) -> str:
        """📋 Obter informações do sistema"""
        hmi_status = "✅ Ativo" if "hmi" in self.services_started else "❌ Inativo"
        
        info = [
            "\n📋 SISTEMA INICIALIZADO:",
            f"   🎯 Detector: {'✅ Ativo' if 'detector' in self.services_started else '❌ Inativo'}",
            f"   🌐 API REST: {'✅ Ativo' if 'api' in self.services_started else '❌ Inativo'}",
            f"   📺 HMI Service: {hmi_status}",
            "",
            "🌐 ENDPOINTS DISPONÍVEIS:",
            "   📱 Dashboard: http://localhost:5173",
            "   📹 Video Stream: http://localhost:5000/video_feed", 
            "   🖼️ Training API: http://localhost:5000/api/training/images",
            "   🌐 WebSocket: ws://localhost:8765"
        ]
        
        if "hmi" in self.services_started:
            info.extend([
                "",
                "📺 HMI:",
                "   📺 URL: http://localhost:8080"
            ])
        
        info.extend([
            "",
            "🎯 FUNCIONALIDADES:",
            "   📷 Streaming de vídeo em tempo real",
            "   🤖 Detecção inteligente de objetos",
            "   📚 Sistema de treinamento adaptativo",
            "   🔌 Integração PLC industrial",
            "   📊 API REST para integração",
            "   🌐 WebSocket para tempo real",
            "   📺 Interface HMI otimizada"
        ])
        
        return "\n".join(info)
    
    def get_status(self) -> dict:
        """📊 Obter status completo do sistema"""
        detector_status = smart_detector.get_system_status()
        api_status = api_app.is_running if hasattr(api_app, 'is_running') else False
        hmi_status = hmi_service.get_status() if "hmi" in self.services_started else {"running": False}
        
        return {
            "running": self.is_running,
            "services": self.services_started,
            "detector": detector_status,
            "api": {
                "running": api_status,
                "endpoints": [
                    "/api/training/images",
                    "/api/system/status",
                    "/video_feed"
                ]
            },
            "hmi": hmi_status,
            "uptime": time.time(),
            "system_info": self._get_system_info()
        }

def main():
    """🏁 Função principal"""
    system = SmartDetectionSystem()
    system.run()

if __name__ == "__main__":
    main()