"""
🎯 Detector Principal - Smart Detection Core (MELHORADO)
"""
import time
import threading
from collections import Counter
from typing import Dict, Optional, List
import numpy as np
import cv2

# Modelos e configurações
from ..models.detection_model import (
    SystemData, DetectionValues, TrainingCounters, SmartCounters,
    ComponentStatus, PLCStatus, DetectionState, SystemStatus
)
from config.settings import DETECTION_CONFIG, COMMUNICATION_CONFIG, MESSAGES

# Serviços
from ..services.camera_service import camera_service
from ..services.websocket_service import websocket_service
from ..utils.image_utils import image_manager

# Imports opcionais para evitar falha na inicialização
try:
    from ..services.plc_service import plc_service
    PLC_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ PLC não disponível: {e}")
    PLC_AVAILABLE = False
    plc_service = None

class SmartDetector:
    """🎯 Detector Principal - Sistema de Detecção Inteligente (MELHORADO)"""

    def __init__(self):
        # Estado do sistema
        self.system_data = SystemData.create_default()
        self.is_running = False

        # Treinamento
        self.training_images = {
            "sem_copo": [],
            "copo_bom": [],
            "copo_danificado": []
        }

        # Detecção
        self.sensitivity = DETECTION_CONFIG["default_sensitivity"]
        self.stability_history = []
        self.last_capture_time = 0

        # Threading
        self.main_thread = None
        self.cycle_counter = 0

        print("🎯 Smart Detector inicializado")

    def initialize_system(self) -> bool:
        """🚀 Inicializar todos os componentes do sistema"""
        print("🚀 Inicializando Smart Detection System...")

        success_components = []

        # 1. Conectar câmera
        if camera_service.connect():
            self.system_data.component_status.camera = True
            success_components.append("📷 Câmera")
        else:
            print("⚠️ Câmera não conectada")

        # 2. Conectar PLC
        if PLC_AVAILABLE and plc_service:
            if plc_service.connect():
                self.system_data.component_status.plc.conectado = True
                self.system_data.component_status.plc.db18_disponivel = plc_service.db18_disponivel
                success_components.append("🔌 PLC")
            else:
                print("⚠️ PLC não conectado")
        else:
            print("⚠️ PLC não disponível (snap7 não instalado)")

        # 3. Iniciar WebSocket
        if websocket_service.start_server():
            self.system_data.component_status.websocket = True
            success_components.append("🌐 WebSocket")
        else:
            print("⚠️ WebSocket não iniciado")

        # 4. Carregar dados de treinamento
        self._load_training_data()

        # 5. Configurar callbacks do WebSocket
        self._setup_websocket_callbacks()

        print(f"✅ Componentes inicializados: {', '.join(success_components)}")
        
        # Após a inicialização, enviar um update inicial para o WebSocket
        self._update_websocket(force=True)
        
        return len(success_components) > 0

    def _load_training_data(self):
        """📚 Carregar dados de treinamento existentes"""
        try:
            stats = image_manager.get_training_stats()

            # Atualizar contadores
            self.system_data.training_counters = TrainingCounters(
                sem_copo=stats.images_by_category.get("sem_copo", 0),
                copo_bom=stats.images_by_category.get("copo_bom", 0),
                copo_danificado=stats.images_by_category.get("copo_danificado", 0)
            )

            # Carregar imagens na memória para detecção
            for category in ["sem_copo", "copo_bom", "copo_danificado"]:
                images = image_manager.get_images_by_category(category)
                self.training_images[category] = []

                for img_info in images:
                    try:
                        img_array = cv2.imread(img_info.path, cv2.IMREAD_GRAYSCALE)
                        if img_array is not None:
                            img_resized = cv2.resize(img_array, (100, 100))
                            self.training_images[category].append(img_resized)
                    except Exception as e:
                        print(f"⚠️ Erro ao carregar {img_info.path}: {e}")

            # Atualizar o status AI_READY
            self.system_data.component_status.ai_ready = self.system_data.training_counters.is_complete()

            print(f"📚 Dados de treinamento carregados: {stats.total_images} imagens")

        except Exception as e:
            print(f"❌ Erro ao carregar dados de treinamento: {e}")
            self.system_data.component_status.ai_ready = False

    def _setup_websocket_callbacks(self):
        """🔧 Configurar callbacks do WebSocket"""
        websocket_service.set_command_callback('train', self._handle_train_command)
        websocket_service.set_command_callback('detect', self._handle_detect_command)
        websocket_service.set_command_callback('reset', self._handle_reset_command)
        websocket_service.set_command_callback('capture_empty', lambda cmd: self._handle_capture_command('sem_copo', cmd))
        websocket_service.set_command_callback('capture_good', lambda cmd: self._handle_capture_command('copo_bom', cmd))
        websocket_service.set_command_callback('capture_damaged', lambda cmd: self._handle_capture_command('copo_danificado', cmd))

        print("🔧 Callbacks do WebSocket configurados")

    def _handle_train_command(self, command: Dict) -> bool:
        """📚 Processar comando de treinamento"""
        try:
            if self.system_data.component_status.ai_ready and self.system_data.status == SystemStatus.DETECCAO:
                self.system_data.status = SystemStatus.AGUARDANDO

            self.system_data.status = SystemStatus.TREINAMENTO
            self.system_data.controles.modo_treinamento = True
            self.system_data.controles.pode_treinar = False
            self.system_data.controles.pode_detectar = False
            self.system_data.controles.pode_capturar = True

            self._update_websocket(force=True)
            print("📚 Modo treinamento ativado")
            return True
        except Exception as e:
            print(f"❌ Erro no comando de treinamento: {e}")
            return False

    def _handle_detect_command(self, command: Dict) -> bool:
        """🎯 Processar comando de detecção"""
        if self.system_data.component_status.ai_ready:
            self.system_data.status = SystemStatus.DETECCAO
            self.system_data.controles.modo_treinamento = False
            self.system_data.controles.pode_treinar = True
            self.system_data.controles.pode_detectar = False
            self.system_data.controles.pode_capturar = False
            
            self._update_websocket(force=True)
            print("🎯 Modo detecção ativado")
            return True
        else:
            print("⚠️ Treinamento incompleto - detecção não disponível")
            websocket_service.broadcast_notification({"message": MESSAGES["training_incomplete"], "level": "ALERT"})
            return False

    def _handle_reset_command(self, command: Dict) -> bool:
        """🔄 Processar comando de reset"""
        self.reset_system()
        self._update_websocket(force=True)
        print("🔄 Sistema resetado")
        return True

    def _handle_capture_command(self, category: str, command: Dict = {}) -> bool:
        """📸 Processar comando de captura"""
        if self.system_data.status != SystemStatus.TREINAMENTO:
            print("⚠️ Sistema não está em modo treinamento")
            websocket_service.broadcast_notification({"message": MESSAGES["not_in_training_mode"], "level": "ALERT"})
            return False

        current_time = time.time()
        if current_time - self.last_capture_time < DETECTION_CONFIG["min_capture_interval"]:
            print("⚠️ Intervalo mínimo entre capturas não respeitado")
            return False

        roi_image = camera_service.capture_roi_image()

        if roi_image is None:
            print("❌ Falha ao capturar imagem da ROI")
            websocket_service.broadcast_notification({"message": MESSAGES["camera_capture_failed"], "level": "ERROR"})
            return False

        filename = image_manager.save_training_image(roi_image, category)

        if filename:
            if category == "sem_copo":
                self.system_data.training_counters.sem_copo += 1
            elif category == "copo_bom":
                self.system_data.training_counters.copo_bom += 1
            elif category == "copo_danificado":
                self.system_data.training_counters.copo_danificado += 1

            roi_image_resized = cv2.resize(roi_image, (100, 100))
            self.training_images[category].append(roi_image_resized.copy())

            self.system_data.component_status.ai_ready = self.system_data.training_counters.is_complete()

            self.last_capture_time = current_time
            print(f"📸 Imagem capturada: {category} ({filename})")
            websocket_service.broadcast_notification({"message": f"Imagem '{category}' capturada com sucesso.", "level": "OK"})
            
            self._update_websocket(force=True)
            return True

        print("❌ Falha ao salvar imagem de treinamento.")
        return False

    def start_detection_loop(self):
        """▶️ Iniciar loop principal de detecção"""
        if self.is_running:
            print("⚠️ Sistema já está rodando")
            return

        self.is_running = True
        self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self.main_thread.name = "SmartDetector-Main"
        self.main_thread.start()

        print("▶️ Loop principal de detecção iniciado")

    def stop_detection_loop(self):
        """⏹️ Parar loop de detecção"""
        self.is_running = False
        print("⏹️ Loop de detecção parado")

    def _main_loop(self):
        """🔄 Loop principal do sistema"""
        print("🔄 Loop principal iniciado")

        while self.is_running:
            try:
                self.system_data.timestamp = time.time()

                # 1. Processar comandos do PLC
                if PLC_AVAILABLE and self.system_data.component_status.plc.conectado and \
                   self.cycle_counter % COMMUNICATION_CONFIG["plc_update_interval"] == 0:
                    self._process_plc_commands()

                # 2. Processar detecção
                if self.system_data.component_status.ai_ready and camera_service.is_connected and \
                   self.system_data.status == SystemStatus.DETECCAO:
                    self._process_detection()

                # 3. Atualizar WebSocket
                if self.cycle_counter % COMMUNICATION_CONFIG["websocket_update_interval"] == 0:
                    self._update_websocket()

                # 4. Atualizar dados do PLC
                if PLC_AVAILABLE and self.system_data.component_status.plc.conectado and \
                   self.cycle_counter % COMMUNICATION_CONFIG["plc_update_interval"] == 0:
                    self._update_plc_data()

                self.cycle_counter += 1
                time.sleep(0.03)

            except Exception as e:
                print(f"❌ Erro no loop principal: {e}")
                time.sleep(0.1)

    def _process_plc_commands(self):
        """🔌 Processar comandos do PLC"""
        if not PLC_AVAILABLE or not plc_service or not self.system_data.component_status.plc.conectado:
            return

        try:
            commands = plc_service.ler_comandos()

            if not commands:
                return

            if 'sensibilidade' in commands:
                self.sensitivity = commands['sensibilidade']
                self.system_data.sensibilidade = self.sensitivity
                self._update_websocket(force=True)

            if commands.get('treinar'):
                self._handle_train_command({})
            
            if commands.get('detectar'):
                self._handle_detect_command({})

            if commands.get('reset'):
                self._handle_reset_command({})

            if self.system_data.status == SystemStatus.TREINAMENTO:
                if commands.get('capturar_sem_copo'):
                    self._handle_capture_command('sem_copo', {})
                if commands.get('capturar_copo_bom'):
                    self._handle_capture_command('copo_bom', {})
                if commands.get('capturar_danificado'):
                    self._handle_capture_command('copo_danificado', {})

        except Exception as e:
            print(f"❌ Erro processando comandos PLC: {e}")

    def _process_detection(self):
        """🔍 Processar detecção de objetos (MELHORADO)"""
        if not camera_service.is_connected:
            return

        # Obter ROI atual
        roi = camera_service.get_roi_from_current_frame()

        if roi is None:
            return

        # Calcular valores de similaridade
        self.system_data.detection_values = self._calculate_detection_values(roi)

        # Aplicar detecção se em modo detecção
        if self.system_data.status == SystemStatus.DETECCAO:
            # CORREÇÃO: Usar diretamente o maior valor
            raw_detection = self._get_best_detection_direct()

            if raw_detection:
                # Aplicar filtro de estabilidade simples
                stable_state = self._apply_simple_stability_filter(raw_detection)
                
                if stable_state != self.system_data.detected_state:
                    # Atualizar estado
                    old_state = self.system_data.detected_state
                    self.system_data.detected_state = stable_state
                    
                    # NOVO: Incrementar contador inteligente
                    if self.system_data.smart_counters.increment_if_changed(stable_state):
                        print(f"🧠 Nova detecção: {old_state.value} → {stable_state.value}")
                        print(f"🔢 Contadores: Bom={self.system_data.smart_counters.copo_bom_count}, "
                              f"Danificado={self.system_data.smart_counters.copo_danificado_count}, "
                              f"Total={self.system_data.smart_counters.total_detections}")
                        
                        # Forçar atualização WebSocket para nova detecção
                        self._update_websocket(force=True)

    def _get_best_detection_direct(self) -> Optional[DetectionState]:
        """🎯 Obter melhor detecção baseada no maior valor (NOVO)"""
        values = self.system_data.detection_values
        
        # Criar mapeamento de valores
        detection_map = {
            DetectionState.SEM_COPO: values.sem_copo,
            DetectionState.COPO_BOM: values.copo_bom,
            DetectionState.COPO_DANIFICADO: values.copo_danificado
        }
        
        # Encontrar o maior valor
        max_state = max(detection_map, key=detection_map.get)
        max_value = detection_map[max_state]
        
        # Verificar se o valor é confiável (acima da sensibilidade)
        if max_value >= self.sensitivity:
            # Verificar diferença com segundo maior
            sorted_values = sorted(detection_map.values(), reverse=True)
            if len(sorted_values) >= 2:
                difference = sorted_values[0] - sorted_values[1]
                if difference >= self.sensitivity * 0.5:  # Margem de confiança
                    return max_state
        
        return None  # Não há detecção confiável

    def _apply_simple_stability_filter(self, detection: DetectionState) -> DetectionState:
        """🔒 Filtro de estabilidade simplificado (MELHORADO)"""
        # Adicionar ao histórico
        self.stability_history.append(detection)
        
        # Manter histórico pequeno (últimas 3 detecções)
        if len(self.stability_history) > 3:
            self.stability_history.pop(0)
        
        # Se temos pelo menos 2 detecções iguais consecutivas, aceitar
        if len(self.stability_history) >= 2:
            last_two = self.stability_history[-2:]
            if last_two[0] == last_two[1]:
                return detection
        
        # Senão, manter estado atual
        return self.system_data.detected_state

    def _calculate_detection_values(self, roi: np.ndarray) -> DetectionValues:
        """📊 Calcular valores de detecção"""
        values = DetectionValues()

        try:
            # Sem copo
            if self.training_images["sem_copo"]:
                values.sem_copo = self._calculate_similarity(roi, self.training_images["sem_copo"])

            # Copo bom
            if self.training_images["copo_bom"]:
                values.copo_bom = self._calculate_similarity(roi, self.training_images["copo_bom"])

            # Copo danificado
            if self.training_images["copo_danificado"]:
                values.copo_danificado = self._calculate_similarity(roi, self.training_images["copo_danificado"])

        except Exception as e:
            print(f"❌ Erro calculando valores de detecção: {e}")

        return values

    def _calculate_similarity(self, roi: np.ndarray, training_images: List[np.ndarray]) -> float:
        """🔍 Calcular similaridade usando template matching"""
        if not training_images or roi is None or roi.size == 0:
            return 0.0

        if roi.shape != (100, 100):
            try:
                roi = cv2.resize(roi, (100, 100))
            except Exception as e:
                print(f"⚠️ Erro ao redimensionar ROI para similaridade: {e}")
                return 0.0

        similarities = []

        for training_img in training_images:
            try:
                if roi.dtype != training_img.dtype:
                    training_img = training_img.astype(roi.dtype)

                result = cv2.matchTemplate(roi, training_img, cv2.TM_CCOEFF_NORMED)
                _, similarity, _, _ = cv2.minMaxLoc(result)
                similarities.append(similarity)
            except cv2.error as e:
                print(f"❌ Erro no template matching: {e}")
                continue
            except Exception as e:
                print(f"❌ Erro inesperado ao calcular similaridade: {e}")
                continue

        if not similarities:
            return 0.0

        # Média das 3 melhores similaridades
        similarities.sort(reverse=True)
        top_similarities = similarities[:min(3, len(similarities))]
        return np.mean(top_similarities)

    def _update_websocket(self, force: bool = False):
        """🌐 Atualizar dados do WebSocket (MELHORADO)"""
        try:
            websocket_data = {
                "timestamp": time.time(),
                "status": self.system_data.status.value,
                "valores": self.system_data.detection_values.to_dict(),
                "contadores": self.system_data.training_counters.to_dict(),
                "contadores_inteligentes": self.system_data.smart_counters.to_dict(),  # NOVO
                "sensibilidade": self.system_data.sensibilidade,
                "treinamento_completo": self.system_data.component_status.ai_ready,
                "plc": self.system_data.component_status.plc.to_dict(),
                "controles": self.system_data.controles.to_dict(),
                "estado_detectado": self.system_data.detected_state.value
            }

            websocket_service.update_data(websocket_data)

        except Exception as e:
            print(f"❌ Erro atualizando WebSocket: {e}")
            fallback_data = {
                "timestamp": time.time(),
                "status": "ERRO_WS",
                "valores": {"sem_copo": 0.0, "copo_bom": 0.0, "copo_danificado": 0.0},
                "contadores": {"sem_copo": 0, "copo_bom": 0, "copo_danificado": 0},
                "contadores_inteligentes": {"sem_copo_count": 0, "copo_bom_count": 0, "copo_danificado_count": 0, "total_detections": 0},
                "plc": {"conectado": False, "db18_disponivel": False},
                "sensibilidade": 0.1,
                "treinamento_completo": self.system_data.component_status.ai_ready,
                "estado_detectado": "ERRO",
                "controles": {
                    "pode_treinar": True,
                    "pode_detectar": False,
                    "pode_capturar": False,
                    "modo_treinamento": False
                }
            }
            websocket_service.update_data(fallback_data)

    def _update_plc_data(self):
        """🔌 Atualizar dados do PLC (MELHORADO)"""
        if not PLC_AVAILABLE or not plc_service or not self.system_data.component_status.plc.conectado:
            return

        try:
            # Enviar valores de detecção
            if self.system_data.component_status.ai_ready:
                plc_service.enviar_valores(
                    self.system_data.detection_values.sem_copo,
                    self.system_data.detection_values.copo_bom,
                    self.system_data.detection_values.copo_danificado
                )

            # MELHORADO: Enviar status com estado baseado no maior valor
            current_state = self.system_data.detected_state.value
            
            plc_service.enviar_status(
                self.system_data.training_counters.is_complete(),
                self.system_data.training_counters.sem_copo,
                self.system_data.training_counters.copo_bom,
                self.system_data.training_counters.copo_danificado,
                current_state
            )

            # Enviar compatibilidade DB17
            plc_service.enviar_db17_compatibilidade(current_state)

        except Exception as e:
            print(f"❌ Erro atualizando PLC: {e}")

    def reset_system(self):
        """🔄 Reset completo do sistema (MELHORADO)"""
        print("🔄 Resetando sistema...")

        # Limpar dados de treinamento
        image_manager.clear_all_training_data()

        # Reset contadores
        self.system_data.training_counters = TrainingCounters()

        # NOVO: Reset contadores inteligentes
        self.system_data.smart_counters.reset()

        # Reset imagens na memória
        for category in self.training_images:
            self.training_images[category] = []

        # Reset estado
        self.system_data.status = SystemStatus.AGUARDANDO
        self.system_data.detected_state = DetectionState.SEM_COPO
        self.system_data.component_status.ai_ready = False
        self.stability_history = []
        
        # Reset controles
        self.system_data.controles.pode_treinar = True
        self.system_data.controles.pode_detectar = False
        self.system_data.controles.pode_capturar = False
        self.system_data.controles.modo_treinamento = False

        print("✅ Sistema resetado (incluindo contadores inteligentes)")

    def shutdown(self):
        """🛑 Finalizar sistema"""
        print("🛑 Finalizando Smart Detector...")

        # Parar loop principal
        self.stop_detection_loop()

        # Desconectar serviços
        camera_service.disconnect()
        if PLC_AVAILABLE and plc_service:
            plc_service.desconectar()
        websocket_service.stop_server()

        print("✅ Smart Detector finalizado")

    def get_system_status(self) -> Dict:
        """📊 Obter status completo do sistema (MELHORADO)"""
        return {
            "running": self.is_running,
            "system_data": self.system_data.to_dict(),
            "training_images_loaded": {
                category: len(images)
                for category, images in self.training_images.items()
            },
            "sensitivity": self.sensitivity,
            "cycle_counter": self.cycle_counter,
            "smart_counters": self.system_data.smart_counters.to_dict()  # NOVO
        }

# 🏭 Instância global do detector
smart_detector = SmartDetector()