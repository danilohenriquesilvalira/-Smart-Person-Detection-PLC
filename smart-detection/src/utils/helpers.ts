// 🛠️ Helper Functions - Smart Detection Dashboard

import type { DetectionState, WebSocketData } from '../types';
import { DETECTION_STATES } from './constants';

export const determineDetectedState = (valores: any): DetectionState => {
  if (!valores) {
    return DETECTION_STATES.SEM_COPO;
  }

  const sem_copo = valores.sem_copo || 0;
  const copo_bom = valores.copo_bom || 0; 
  const copo_danificado = valores.copo_danificado || 0;

  let detectedState: DetectionState = DETECTION_STATES.SEM_COPO;
  let maxVal = sem_copo;

  if (copo_bom > maxVal) {
    maxVal = copo_bom;
    detectedState = DETECTION_STATES.COPO_BOM;
  }
  
  if (copo_danificado > maxVal) {
    maxVal = copo_danificado;
    detectedState = DETECTION_STATES.COPO_DANIFICADO;
  }

  return detectedState;
};

/**
 * Retorna as classes CSS para o background baseado no estado
 */
export const getEstadoBgClass = (estado: DetectionState): string => {
  switch (estado) {
    case DETECTION_STATES.COPO_BOM:
      return 'bg-green-100 text-green-800';
    case DETECTION_STATES.COPO_DANIFICADO:
      return 'bg-red-100 text-red-800';
    case DETECTION_STATES.SEM_COPO:
      return 'bg-gray-100 text-gray-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

/**
 * Retorna as propriedades do ícone para o estado de detecção
 */
export const getDetectionIconProps = (estado: DetectionState) => {
  switch (estado) {
    case DETECTION_STATES.COPO_BOM:
      return { src: "/Com_Copo.svg", alt: "Copo Bom", className: "w-6 h-6 ml-2" };
    case DETECTION_STATES.COPO_DANIFICADO:
      return { src: "/Copo_Danificado.svg", alt: "Copo Danificado", className: "w-6 h-6 ml-2" };
    case DETECTION_STATES.SEM_COPO:
      return { src: "/Sem_Copo.svg", alt: "Sem Copo", className: "w-6 h-6 ml-2" };
    default:
      return null;
  }
};

/**
 * Calcula o progresso de treinamento
 */
export const calculateTrainingProgress = (contadores: WebSocketData['contadores']) => {
  const total = contadores.sem_copo + contadores.copo_bom + contadores.copo_danificado;
  return {
    total,
    percentage: (total / 30) * 100,
    isComplete: total >= 30
  };
};

/**
 * Formata mensagem de log com timestamp
 */
export const formatLogMessage = (message: string, type: string): string => {
  const timestamp = new Date().toLocaleTimeString('pt-BR');
  const prefix = `[${type}]`;
  return `> ${prefix} ${timestamp}: ${message}`;
};

/**
 * Calcula o delay para reconexão WebSocket
 */
export const calculateReconnectDelay = (attempts: number): number => {
  return Math.min(1000 + (attempts * 500), 5000);
};

/**
 * Valida se os dados WebSocket estão completos
 */
export const validateWebSocketData = (data: any): data is WebSocketData => {
  return (
    data &&
    typeof data.timestamp === 'number' &&
    typeof data.status === 'string' &&
    data.valores &&
    data.contadores &&
    data.plc &&
    typeof data.sensibilidade === 'number' &&
    typeof data.treinamento_completo === 'boolean'
  );
};

/**
 * Gera estado mapeado para string amigável
 */
export const getStateDisplayName = (estado: DetectionState): string => {
  const stateMap = {
    [DETECTION_STATES.SEM_COPO]: 'Sem Copo',
    [DETECTION_STATES.COPO_BOM]: 'Copo Bom',
    [DETECTION_STATES.COPO_DANIFICADO]: 'Copo Danificado'
  };

  return stateMap[estado] || estado.replace('_', ' ');
};

/**
 * Retorna a classe CSS da cor do círculo de status baseado no estado
 */
export const getStatusCircleClass = (estado: DetectionState): string => {
  switch (estado) {
    case DETECTION_STATES.COPO_BOM:
      return 'bg-green-500';
    case DETECTION_STATES.COPO_DANIFICADO:
      return 'bg-red-500';
    case DETECTION_STATES.SEM_COPO:
      return 'bg-gray-500';
    default:
      return 'bg-gray-500';
  }
};