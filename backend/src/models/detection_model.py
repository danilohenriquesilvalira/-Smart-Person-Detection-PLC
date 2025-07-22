"""
📊 Modelos de Detecção - Smart Detection Backend
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
    INCERTO = "INCERTO" # Adicionado para cobrir estados indefinidos na detecção

class SystemStatus(Enum):
    """🔧 Status do sistema"""
    AGUARDANDO = "AGUARDANDO"
    TREINAMENTO = "TREINAMENTO"
    DETECCAO = "DETECCAO"
    ERRO = "ERRO" # Adicionado para representar um estado de erro

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
        """🎯 Obter estado com maior valor"""
        valores = {
            DetectionState.SEM_COPO: self.sem_copo,
            DetectionState.COPO_BOM: self.copo_bom,
            DetectionState.COPO_DANIFICADO: self.copo_danificado
        }
        # Retorna o estado com o maior valor, ou INCERTO se todos forem zero ou negativos
        if all(v <= 0 for v in valores.values()):
            return DetectionState.INCERTO
        return max(valores, key=valores.get)

@dataclass
class TrainingCounters:
    """🔢 Contadores de treinamento"""
    sem_copo: int = 0
    copo_bom: int = 0
    copo_danificado: int = 0
    # Definindo o target aqui, ou você pode importar de config.settings se preferir centralizar
    TRAINING_TARGET_PER_CATEGORY: int = 10

    def to_dict(self) -> Dict:
        """🔄 Converter para dicionário"""
        return asdict(self)

    def is_complete(self) -> bool:
        """✅ Verificar se treinamento está completo baseado no target"""
        return (self.sem_copo >= self.TRAINING_TARGET_PER_CATEGORY and
                self.copo_bom >= self.TRAINING_TARGET_PER_CATEGORY and
                self.copo_danificado >= self.TRAINING_TARGET_PER_CATEGORY)

    def get_completion_percentage(self) -> float:
        """Calcula a porcentagem de conclusão do treinamento."""
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
    """🔧 Status dos componentes de hardware/serviço (Câmera, PLC, WebSocket, AI)"""
    camera: bool = False
    plc: PLCStatus = field(default_factory=PLCStatus) # Usar field(default_factory=...) para tipos mutáveis
    websocket: bool = False
    ai_ready: bool = False # Indica se a AI tem dados de treinamento suficientes para operar

    def to_dict(self) -> Dict:
        """🔄 Converter para dicionário"""
        return {
            "camera": self.camera,
            "plc": self.plc.to_dict(),
            "websocket": self.websocket,
            "ai_ready": self.ai_ready
        }

@dataclass
class ControlStatus: # <--- NOVA CLASSE PARA OS CONTROLES DA UI/LÓGICA
    """💡 Status e controles para a interface e lógica do sistema."""
    pode_treinar: bool = True
    pode_detectar: bool = False
    pode_capturar: bool = False
    modo_treinamento: bool = False # Indica se o sistema está no modo de coleta de imagens

    def to_dict(self) -> Dict:
        """🔄 Converter para dicionário"""
        return asdict(self)

@dataclass
class SystemData:
    """🎯 Dados completos do sistema que serão enviados ao frontend."""
    timestamp: float = field(default_factory=time.time) # Usar default_factory para timestamp
    status: SystemStatus = SystemStatus.AGUARDANDO
    detection_values: DetectionValues = field(default_factory=DetectionValues)
    training_counters: TrainingCounters = field(default_factory=TrainingCounters)
    component_status: ComponentStatus = field(default_factory=ComponentStatus)
    
    # ATENÇÃO: AQUI ESTÁ A CORREÇÃO CRÍTICA!
    controles: ControlStatus = field(default_factory=ControlStatus) # Agora SystemData tem o atributo 'controles'

    detected_state: DetectionState = DetectionState.SEM_COPO
    sensibilidade: float = 0.1
    # O campo 'treinamento_completo' é redundante aqui se você já tem ai_ready em component_status
    # e o calcula no detector.py. Eu o removeria daqui e usaria component_status.ai_ready diretamente.
    # Mas se você quer mantê-lo para clareza no JSON, é ok. Eu ajustei o to_dict para usar ai_ready.
    treinamento_completo: bool = False # Este será atualizado em __post_init__ ou pelo detector

    def __post_init__(self):
        """🔄 Pós-processamento: Garante que os valores iniciais estão corretos."""
        # Se timestamp não foi fornecido, define agora
        if self.timestamp is None:
            self.timestamp = time.time()
        
        # O detected_state deve ser determinado pela lógica de detecção no Detector
        # e não necessariamente pelo max_state dos valores brutos aqui,
        # a menos que seja um estado inicial ou de fallback.
        # Vou manter a linha, mas o detector.py deve definir isso para detecção ativa.
        # if self.detection_values:
        #     self.detected_state = self.detection_values.get_max_state()
        
        # O treinamento_completo é melhor gerado a partir do component_status.ai_ready
        # que é atualizado no detector.py
        if self.training_counters:
             self.treinamento_completo = self.training_counters.is_complete()


    def to_dict(self) -> Dict:
        """🔄 Converter para dicionário compatível com WebSocket"""
        return {
            "timestamp": self.timestamp,
            "status": self.status.value,
            "valores": self.detection_values.to_dict(),
            "contadores": self.training_counters.to_dict(),
            "plc": self.component_status.plc.to_dict(),
            "sensibilidade": self.sensibilidade,
            # Usar component_status.ai_ready como a fonte da verdade para 'treinamento_completo'
            "treinamento_completo": self.component_data.ai_ready, # <--- Corrigido para usar ai_ready
            "estado_detectado": self.detected_state.value,
            # Agora 'controles' é um atributo real de SystemData e tem seu próprio to_dict()
            "controles": self.controles.to_dict() # <--- CORREÇÃO AQUI
        }

    @classmethod
    def create_default(cls) -> 'SystemData':
        """🏭 Criar instância padrão com valores válidos"""
        # Ao criar o default, certifique-se de inicializar todos os dataclasses aninhados
        return cls(
            timestamp=time.time(),
            status=SystemStatus.AGUARDANDO,
            detection_values=DetectionValues(),
            training_counters=TrainingCounters(),
            component_status=ComponentStatus(), # Isso inicializará PLCStatus internamente
            controles=ControlStatus(),          # <--- INICIALIZANDO O NOVO ATRIBUTO CONTROLES
            detected_state=DetectionState.SEM_COPO,
            sensibilidade=0.1,
            # treinamento_completo será calculado no __post_init__ ou pelo detector
            treinamento_completo=False 
        )

@dataclass
class WebSocketCommand:
    """📨 Comando recebido via WebSocket"""
    action: str
    data: Optional[Dict] = None
    timestamp: float = field(default_factory=time.time) # Usar default_factory

@dataclass
class TrainingImage:
    """🖼️ Informações de imagem de treinamento"""
    filename: str
    category: str
    path: str
    created_at: float = field(default_factory=time.time) # Usar default_factory
    size: int = 0 # Adicionado valor padrão

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