"""
📊 Modelos de Detecção - Smart Detection Backend (MELHORADO)
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from enum import Enum
import time

class DetectionState(Enum):
    """🎯 Estados de detecção possíveis"""
    SEM_COPO = "SEM_COPO"
    COPO_BOM = "COPO_BOM"
    COPO_DANIFICADO = "COPO_DANIFICADO"
    INCERTO = "INCERTO"

class SystemStatus(Enum):
    """🔧 Status do sistema"""
    AGUARDANDO = "AGUARDANDO"
    TREINAMENTO = "TREINAMENTO"
    DETECCAO = "DETECCAO"
    ERRO = "ERRO"

@dataclass
class DetectionValues:
    """📊 Valores de detecção medidos"""
    sem_copo: float = 0.0
    copo_bom: float = 0.0
    copo_danificado: float = 0.0

    def to_dict(self) -> Dict:
        """🔄 Converter para dicionário"""
        return asdict(self)

    def get_max_state(self) -> DetectionState:
        """🎯 Obter estado com maior valor (CORRIGIDO)"""
        valores = {
            DetectionState.SEM_COPO: self.sem_copo,
            DetectionState.COPO_BOM: self.copo_bom,
            DetectionState.COPO_DANIFICADO: self.copo_danificado
        }
        
        # Se todos os valores forem muito baixos, retorna INCERTO
        if all(v < 0.3 for v in valores.values()):
            return DetectionState.INCERTO
            
        # Retorna o estado com maior valor
        return max(valores, key=valores.get)

@dataclass
class SmartCounters:
    """🧠 Contadores Inteligentes (CORRIGIDO)"""
    sem_copo_count: int = 0
    copo_bom_count: int = 0
    copo_danificado_count: int = 0
    total_detections: int = 0
    last_state: DetectionState = DetectionState.SEM_COPO

    def increment_if_changed(self, new_state: DetectionState) -> bool:
        """➕ Incrementa contador apenas se estado mudou"""
        if new_state != self.last_state and new_state != DetectionState.INCERTO:
            if new_state == DetectionState.SEM_COPO:
                self.sem_copo_count += 1
            elif new_state == DetectionState.COPO_BOM:
                self.copo_bom_count += 1
            elif new_state == DetectionState.COPO_DANIFICADO:
                self.copo_danificado_count += 1
            
            self.total_detections += 1
            self.last_state = new_state
            return True
        return False

    def to_dict(self) -> Dict:
        """🔄 Converter para dicionário (CORRIGIDO)"""
        return {
            "sem_copo_count": self.sem_copo_count,
            "copo_bom_count": self.copo_bom_count,
            "copo_danificado_count": self.copo_danificado_count,
            "total_detections": self.total_detections,
            "last_state": self.last_state.value  # CORREÇÃO: usar .value
        }

    def reset(self):
        """🔄 Resetar contadores"""
        self.sem_copo_count = 0
        self.copo_bom_count = 0
        self.copo_danificado_count = 0
        self.total_detections = 0
        self.last_state = DetectionState.SEM_COPO

@dataclass
class TrainingCounters:
    """🔢 Contadores de treinamento"""
    sem_copo: int = 0
    copo_bom: int = 0
    copo_danificado: int = 0
    TRAINING_TARGET_PER_CATEGORY: int = 10

    def to_dict(self) -> Dict:
        """🔄 Converter para dicionário"""
        return asdict(self)

    def is_complete(self) -> bool:
        """✅ Verificar se treinamento está completo"""
        return (self.sem_copo >= self.TRAINING_TARGET_PER_CATEGORY and
                self.copo_bom >= self.TRAINING_TARGET_PER_CATEGORY and
                self.copo_danificado >= self.TRAINING_TARGET_PER_CATEGORY)

    def get_completion_percentage(self) -> float:
        """📊 Porcentagem de conclusão do treinamento"""
        total_required = self.TRAINING_TARGET_PER_CATEGORY * 3
        total_current = min(self.sem_copo, self.TRAINING_TARGET_PER_CATEGORY) + \
                        min(self.copo_bom, self.TRAINING_TARGET_PER_CATEGORY) + \
                        min(self.copo_danificado, self.TRAINING_TARGET_PER_CATEGORY)
        
        if total_required == 0:
            return 0.0
        return (total_current / total_required) * 100

@dataclass
class PLCStatus:
    """🔌 Status do PLC"""
    conectado: bool = False
    db18_disponivel: bool = False

    def to_dict(self) -> Dict:
        """🔄 Converter para dicionário"""
        return asdict(self)

@dataclass
class ComponentStatus:
    """🔧 Status dos componentes"""
    camera: bool = False
    plc: PLCStatus = field(default_factory=PLCStatus)
    websocket: bool = False
    ai_ready: bool = False

    def to_dict(self) -> Dict:
        """🔄 Converter para dicionário"""
        return {
            "camera": self.camera,
            "plc": self.plc.to_dict(),
            "websocket": self.websocket,
            "ai_ready": self.ai_ready
        }

@dataclass
class ControlStatus:
    """💡 Status e controles para a interface"""
    pode_treinar: bool = True
    pode_detectar: bool = False
    pode_capturar: bool = False
    modo_treinamento: bool = False

    def to_dict(self) -> Dict:
        """🔄 Converter para dicionário"""
        return asdict(self)

@dataclass
class SystemData:
    """🎯 Dados completos do sistema (MELHORADO)"""
    timestamp: float = field(default_factory=time.time)
    status: SystemStatus = SystemStatus.AGUARDANDO
    detection_values: DetectionValues = field(default_factory=DetectionValues)
    training_counters: TrainingCounters = field(default_factory=TrainingCounters)
    component_status: ComponentStatus = field(default_factory=ComponentStatus)
    controles: ControlStatus = field(default_factory=ControlStatus)
    smart_counters: SmartCounters = field(default_factory=SmartCounters)  # NOVO
    detected_state: DetectionState = DetectionState.SEM_COPO
    sensibilidade: float = 0.1
    treinamento_completo: bool = False

    def __post_init__(self):
        """🔄 Pós-processamento"""
        if self.timestamp is None:
            self.timestamp = time.time()
        
        if self.training_counters:
             self.treinamento_completo = self.training_counters.is_complete()

    def to_dict(self) -> Dict:
        """🔄 Converter para dicionário WebSocket (MELHORADO)"""
        return {
            "timestamp": self.timestamp,
            "status": self.status.value,
            "valores": self.detection_values.to_dict(),
            "contadores": self.training_counters.to_dict(),
            "contadores_inteligentes": self.smart_counters.to_dict(),  # NOVO
            "plc": self.component_status.plc.to_dict(),
            "sensibilidade": self.sensibilidade,
            "treinamento_completo": self.component_status.ai_ready,
            "estado_detectado": self.detected_state.value,
            "controles": self.controles.to_dict()
        }

    @classmethod
    def create_default(cls) -> 'SystemData':
        """🏭 Criar instância padrão"""
        return cls(
            timestamp=time.time(),
            status=SystemStatus.AGUARDANDO,
            detection_values=DetectionValues(),
            training_counters=TrainingCounters(),
            component_status=ComponentStatus(),
            controles=ControlStatus(),
            smart_counters=SmartCounters(),  # NOVO
            detected_state=DetectionState.SEM_COPO,
            sensibilidade=0.1,
            treinamento_completo=False 
        )

@dataclass
class WebSocketCommand:
    """📨 Comando recebido via WebSocket"""
    action: str
    data: Optional[Dict] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class TrainingImage:
    """🖼️ Informações de imagem de treinamento"""
    filename: str
    category: str
    path: str
    created_at: float = field(default_factory=time.time)
    size: int = 0

    def to_dict(self) -> Dict:
        """🔄 Converter para dicionário"""
        return asdict(self)

@dataclass
class TrainingStats:
    """📊 Estatísticas de treinamento"""
    total_images: int
    images_by_category: Dict[str, int]
    training_complete: bool
    completion_percentage: float
    categories: List[str]

    def to_dict(self) -> Dict:
        """🔄 Converter para dicionário"""
        return asdict(self)