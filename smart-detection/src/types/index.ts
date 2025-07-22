// 🔷 Types - Smart Detection Dashboard (ATUALIZADO)

export interface WebSocketData {
  timestamp: number;
  status: 'AGUARDANDO' | 'TREINAMENTO' | 'DETECCAO';
  valores: {
    sem_copo: number;
    copo_bom: number;
    copo_danificado: number;
  };
  contadores: {
    sem_copo: number;
    copo_bom: number;
    copo_danificado: number;
  };
  // NOVO: Contadores Inteligentes
  contadores_inteligentes?: {
    sem_copo_count: number;
    copo_bom_count: number;
    copo_danificado_count: number;
    total_detections: number;
    last_state: string;
  };
  sensibilidade: number;
  treinamento_completo: boolean;
  estado_detectado?: string;
  plc: {
    conectado: boolean;
    db18_disponivel: boolean;
  };
  controles?: {
    pode_treinar: boolean;
    pode_detectar: boolean;
    pode_capturar: boolean;
    modo_treinamento: boolean;
  };
}

export type DetectionState = 'SEM_COPO' | 'COPO_BOM' | 'COPO_DANIFICADO';
export type CaptureType = 'empty' | 'good' | 'damaged';
export type LogType = 'INFO' | 'OK' | 'ALERT' | 'ERROR' | 'DEBUG';

export interface TrainingStep {
  id: CaptureType;
  title: string;
  description: string;
  icon: string;
  color: 'gray' | 'green' | 'red';
  bgColor: string;
  borderColor: string;
  buttonColor: string;
  count: number;
  target: number;
  action: `capture_${CaptureType}`;
}

export interface ComponentStatus {
  name: string;
  icon: React.ComponentType<any>;
  isOnline: boolean;
  label: string;
}

export interface WebSocketCommand {
  action: string;
  [key: string]: any;
}

export interface UseWebSocketReturn {
  data: WebSocketData;
  isConnected: boolean;
  attempts: number;
  sendCommand: (command: WebSocketCommand) => void;
  logMessages: string[];
  addLogMessage: (message: string, type?: LogType) => void;
}