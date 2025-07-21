import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Wifi,
  Settings,
  Play,
  Cpu,
  Database,
  PlayCircle,
  Square,
  RotateCcw,
  Camera,
  CheckCircle,
  XCircle,
  MinusCircle,
  ArrowRight,
  ArrowLeft,
  Check,
  AlertCircle
} from 'lucide-react';

// Tipos
interface WebSocketData {
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
  sensibilidade: number;
  treinamento_completo: boolean;
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

// Hook WebSocket (mantém o mesmo)
const useWebSocket = (url: string = 'ws://localhost:8765') => {
  const [data, setData] = useState<WebSocketData>({
    timestamp: Date.now() / 1000,
    status: "AGUARDANDO",
    valores: { sem_copo: 0.0, copo_bom: 0.0, copo_danificado: 0.0 },
    contadores: { sem_copo: 0, copo_bom: 0, copo_danificado: 0 },
    sensibilidade: 0.1,
    treinamento_completo: false,
    plc: { conectado: false, db18_disponivel: false },
    controles: {
      pode_treinar: true,
      pode_detectar: false,
      pode_capturar: false,
      modo_treinamento: false
    }
  });

  const [isConnected, setIsConnected] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const [logMessages, setLogMessages] = useState<string[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  const addLogMessage = useCallback((message: string, type: 'INFO' | 'OK' | 'ALERT' | 'ERROR' | 'DEBUG' = 'INFO') => {
    const timestamp = new Date().toLocaleTimeString('pt-BR');
    let prefix = '';
    switch (type) {
      case 'OK': prefix = '[OK]'; break;
      case 'ALERT': prefix = '[ALERTA]'; break;
      case 'ERROR': prefix = '[ERRO]'; break;
      case 'DEBUG': prefix = '[DEBUG]'; break;
      case 'INFO':
      default: prefix = '[INFO]'; break;
    }
    setLogMessages(prevLogs => {
      const newLogs = [`> ${prefix} ${timestamp}: ${message}`, ...prevLogs];
      return newLogs.slice(0, 10);
    });
  }, []);

  const sendCommand = useCallback((command: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        const commandString = JSON.stringify(command);
        wsRef.current.send(commandString);
        addLogMessage(`Comando enviado: ${command.action}`, 'INFO');
      } catch (e) {
        console.error('Erro enviando comando:', e);
        addLogMessage(`Erro enviando comando: ${e}`, 'ERROR');
      }
    } else {
      addLogMessage('WebSocket não conectado. Comando não enviado.', 'ALERT');
    }
  }, [addLogMessage]);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onclose = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror = null;
      try { wsRef.current.close(); } catch { }
      wsRef.current = null;
    }

    if (reconnectRef.current) {
      clearTimeout(reconnectRef.current);
      reconnectRef.current = null;
    }

    try {
      wsRef.current = new WebSocket(url);
      addLogMessage(`Conectando ao sistema...`, 'INFO');

      wsRef.current.onopen = () => {
        if (!mountedRef.current) return;
        setIsConnected(true);
        setAttempts(0);
        addLogMessage('Sistema conectado - Controles ativos', 'OK');
      };

      wsRef.current.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const rawData: WebSocketData = JSON.parse(event.data);
          setData(rawData);
        } catch (e) {
          console.warn('Erro no JSON:', e);
          addLogMessage(`Erro ao parsear dados: ${e}`, 'ERROR');
        }
      };

      wsRef.current.onclose = () => {
        if (!mountedRef.current) return;
        setIsConnected(false);
        addLogMessage('Conexão perdida. Reconectando...', 'ALERT');

        const delay = Math.min(1000 + (attempts * 500), 5000);
        reconnectRef.current = setTimeout(() => {
          if (mountedRef.current) {
            setAttempts(prev => prev + 1);
            connect();
          }
        }, delay);
      };

      wsRef.current.onerror = () => {
        if (!mountedRef.current) return;
        setIsConnected(false);
        addLogMessage(`Sistema offline`, 'ERROR');
      };

    } catch (e) {
      if (mountedRef.current) {
        addLogMessage(`Falha na conexão: ${e}`, 'ERROR');
        reconnectRef.current = setTimeout(() => {
          if (mountedRef.current) {
            setAttempts(prev => prev + 1);
            connect();
          }
        }, 2000);
      }
    }
  }, [url, attempts, addLogMessage]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  useEffect(() => {
    if (!isConnected) {
      const interval = setInterval(() => {
        if (mountedRef.current) {
          setData(prev => ({ ...prev, timestamp: Date.now() / 1000 }));
        }
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [isConnected]);

  return { data, isConnected, attempts, sendCommand, logMessages, addLogMessage };
};

// Componente do Modal de Treinamento Moderno
interface TrainingModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: WebSocketData;
  isConnected: boolean;
  onCapture: (type: 'empty' | 'good' | 'damaged') => void;
  videoFeedUrl: string;
  isVideoError: boolean;
}

const TrainingModal: React.FC<TrainingModalProps> = ({
  isOpen,
  onClose,
  data,
  isConnected,
  onCapture,
  videoFeedUrl,
  isVideoError
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isCapturing, setIsCapturing] = useState(false);

  const steps = [
    {
      id: 'empty',
      title: 'Sem Copo',
      description: 'Posicione a esteira sem nenhum copo e capture 10 amostras',
      icon: '/Sem_Copo.svg',
      color: 'gray',
      bgColor: 'bg-gray-50',
      borderColor: 'border-gray-200',
      buttonColor: 'bg-gray-500 hover:bg-gray-600',
      count: data.contadores.sem_copo,
      target: 10,
      action: 'capture_empty' as const
    },
    {
      id: 'good',
      title: 'Copo Bom',
      description: 'Posicione um copo em perfeito estado e capture 10 amostras',
      icon: '/Com_Copo.svg',
      color: 'green',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      buttonColor: 'bg-green-500 hover:bg-green-600',
      count: data.contadores.copo_bom,
      target: 10,
      action: 'capture_good' as const
    },
    {
      id: 'damaged',
      title: 'Copo Danificado',
      description: 'Posicione um copo danificado/amassado e capture 10 amostras',
      icon: '/Copo_Danificado.svg',
      color: 'red',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      buttonColor: 'bg-red-500 hover:bg-red-600',
      count: data.contadores.copo_danificado,
      target: 10,
      action: 'capture_damaged' as const
    }
  ];

  const currentStepData = steps[currentStep];
  const isCurrentStepComplete = currentStepData.count >= currentStepData.target;
  const canGoNext = currentStep < steps.length - 1 && isCurrentStepComplete;
  const canGoPrevious = currentStep > 0;
  const isTrainingComplete = steps.every(step => step.count >= step.target);

  const handleCapture = async () => {
    setIsCapturing(true);
    onCapture(currentStepData.action.replace('capture_', '') as 'empty' | 'good' | 'damaged');
    
    // Simula um pequeno delay para feedback visual
    setTimeout(() => {
      setIsCapturing(false);
    }, 500);
  };

  const handleNext = () => {
    if (canGoNext) {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handlePrevious = () => {
    if (canGoPrevious) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleFinish = () => {
    onClose();
    setCurrentStep(0);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-3xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden transform transition-all">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-800 text-white p-6">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-2xl font-bold">Treinamento Inteligente</h3>
              <p className="text-blue-100 mt-1">Captura guiada de amostras para IA</p>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:text-gray-200 transition-colors p-2 hover:bg-white hover:bg-opacity-20 rounded-full">
              <XCircle className="w-6 h-6" />
            </button>
          </div>
          
          {/* Progress Stepper */}
          <div className="mt-6 flex items-center justify-between">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center">
                <div className={`flex items-center justify-center w-12 h-12 rounded-full border-2 transition-all ${
                  index === currentStep 
                    ? 'bg-white text-blue-600 border-white' 
                    : index < currentStep || step.count >= step.target
                      ? 'bg-green-500 text-white border-green-500'
                      : 'bg-transparent text-white border-white border-opacity-50'
                }`}>
                  {step.count >= step.target ? (
                    <Check className="w-6 h-6" />
                  ) : (
                    <img src={step.icon} alt={step.title} className="w-6 h-6" />
                  )}
                </div>
                <div className="ml-3 hidden sm:block">
                  <div className={`text-sm font-medium ${
                    index === currentStep ? 'text-white' : 'text-blue-100'
                  }`}>
                    {step.title}
                  </div>
                  <div className="text-xs text-blue-100">
                    {step.count}/{step.target} amostras
                  </div>
                </div>
                {index < steps.length - 1 && (
                  <ArrowRight className="w-4 h-4 text-blue-200 mx-4 hidden sm:block" />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Camera Feed */}
            <div className="space-y-4">
              <h4 className="text-lg font-semibold text-gray-900 flex items-center">
                <Camera className="w-5 h-5 mr-2 text-blue-600" />
                Visualização em Tempo Real
              </h4>
              
              <div className="relative w-full rounded-xl border-2 border-gray-200 bg-gray-900 overflow-hidden" style={{ paddingBottom: '56.25%' }}>
                {!isVideoError ? (
                  <img
                    src={videoFeedUrl}
                    alt="Video Stream"
                    className={`absolute inset-0 w-full h-full object-contain ${!isConnected ? 'grayscale' : ''} transition-all duration-500`}
                  />
                ) : (
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-white text-center p-4">
                    <AlertCircle className="w-16 h-16 mb-4 text-red-400" />
                    <p className="text-xl font-semibold">Câmera Offline</p>
                    <p className="text-sm text-gray-400 mt-2">Verifique a conexão do servidor.</p>
                  </div>
                )}
                
                {/* Overlay de Status */}
                <div className="absolute bottom-4 left-4 right-4">
                  <div className={`p-3 rounded-lg ${currentStepData.bgColor} ${currentStepData.borderColor} border backdrop-blur-sm bg-opacity-90`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <img src={currentStepData.icon} alt={currentStepData.title} className="w-6 h-6 mr-2" />
                        <span className="font-medium text-gray-800">{currentStepData.title}</span>
                      </div>
                      <div className="text-sm font-mono text-gray-600">
                        {currentStepData.count}/{currentStepData.target}
                      </div>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                      <div
                        className={`h-2 rounded-full transition-all duration-500 ${
                          currentStepData.color === 'gray' ? 'bg-gray-500' :
                          currentStepData.color === 'green' ? 'bg-green-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${(currentStepData.count / currentStepData.target) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Instructions and Controls */}
            <div className="space-y-6">
              <div className={`p-6 rounded-xl ${currentStepData.bgColor} ${currentStepData.borderColor} border`}>
                <div className="flex items-center mb-4">
                  <img src={currentStepData.icon} alt={currentStepData.title} className="w-8 h-8 mr-3" />
                  <h4 className="text-xl font-bold text-gray-900">{currentStepData.title}</h4>
                </div>
                
                <p className="text-gray-700 mb-6">{currentStepData.description}</p>
                
                {/* Progress Circle */}
                <div className="flex items-center justify-center mb-6">
                  <div className="relative w-24 h-24">
                    <svg className="w-24 h-24 transform -rotate-90" viewBox="0 0 36 36">
                      <path
                        className="text-gray-300"
                        stroke="currentColor"
                        strokeWidth="3"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      <path
                        className={`${
                          currentStepData.color === 'gray' ? 'text-gray-500' :
                          currentStepData.color === 'green' ? 'text-green-500' : 'text-red-500'
                        }`}
                        stroke="currentColor"
                        strokeWidth="3"
                        fill="none"
                        strokeDasharray={`${(currentStepData.count / currentStepData.target) * 100}, 100`}
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-2xl font-bold text-gray-800">{currentStepData.count}</span>
                      <span className="text-sm text-gray-600">/{currentStepData.target}</span>
                    </div>
                  </div>
                </div>

                {/* Capture Button */}
                <button
                  onClick={handleCapture}
                  disabled={!isConnected || isCurrentStepComplete || isCapturing}
                  className={`w-full py-4 px-6 rounded-xl text-white font-semibold transition-all transform ${currentStepData.buttonColor} disabled:opacity-50 disabled:cursor-not-allowed ${
                    isCapturing ? 'scale-95' : 'hover:scale-105'
                  } shadow-lg`}>
                  {isCapturing ? (
                    <div className="flex items-center justify-center">
                      <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-opacity-30 border-t-white mr-2"></div>
                      Capturando...
                    </div>
                  ) : isCurrentStepComplete ? (
                    <div className="flex items-center justify-center">
                      <Check className="w-5 h-5 mr-2" />
                      Etapa Concluída
                    </div>
                  ) : (
                    <div className="flex items-center justify-center">
                      <Camera className="w-5 h-5 mr-2" />
                      Capturar Amostra
                    </div>
                  )}
                </button>

                {isCurrentStepComplete && (
                  <div className="mt-4 p-3 bg-green-100 border border-green-200 rounded-lg">
                    <div className="flex items-center text-green-800">
                      <CheckCircle className="w-5 h-5 mr-2" />
                      <span className="text-sm font-medium">Etapa concluída com sucesso!</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Overall Progress */}
              <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-700">Progresso Geral</span>
                  <span className="text-sm font-mono text-gray-600">
                    {data.contadores.sem_copo + data.contadores.copo_bom + data.contadores.copo_danificado}/30
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-blue-800 h-3 rounded-full transition-all duration-500"
                    style={{ width: `${((data.contadores.sem_copo + data.contadores.copo_bom + data.contadores.copo_danificado) / 30) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex justify-between items-center">
          <button
            onClick={handlePrevious}
            disabled={!canGoPrevious}
            className="flex items-center px-4 py-2 text-gray-600 hover:text-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Anterior
          </button>

          <div className="flex items-center space-x-2">
            {steps.map((_, index) => (
              <div
                key={index}
                className={`w-2 h-2 rounded-full transition-all ${
                  index === currentStep 
                    ? 'bg-blue-600 w-8' 
                    : index < currentStep || steps[index].count >= steps[index].target
                      ? 'bg-green-500'
                      : 'bg-gray-300'
                }`}
              />
            ))}
          </div>

          {isTrainingComplete ? (
            <button
              onClick={handleFinish}
              className="flex items-center px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium">
              <Check className="w-4 h-4 mr-2" />
              Finalizar
            </button>
          ) : (
            <button
              onClick={handleNext}
              disabled={!canGoNext}
              className="flex items-center px-4 py-2 text-blue-600 hover:text-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
              Próximo
              <ArrowRight className="w-4 h-4 ml-2" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// Dashboard Principal
const Dashboard: React.FC = () => {
  const { data, isConnected, sendCommand, logMessages, addLogMessage } = useWebSocket();

  const prevDetectedStateRef = useRef<'SEM_COPO' | 'COPO_BOM' | 'COPO_DANIFICADO' | null>(null);
  const [isVideoError, setIsVideoError] = useState(false);
  const [showTrainingModal, setShowTrainingModal] = useState(false);

  // COMANDOS DO FRONTEND
  const handleTreinar = () => {
    setShowTrainingModal(true);
    sendCommand({ action: 'train' });
    addLogMessage('Iniciando modo treinamento...', 'INFO');
  };

  const handleDetectar = () => {
    if (data.treinamento_completo) {
      sendCommand({ action: 'detect' });
      addLogMessage('Iniciando detecção...', 'OK');
    } else {
      addLogMessage('Treinamento incompleto. Complete o treinamento primeiro.', 'ALERT');
    }
  };

  const handleReset = () => {
    sendCommand({ action: 'reset' });
    addLogMessage('Resetando sistema...', 'ALERT');
  };

  const handleCapture = (type: 'empty' | 'good' | 'damaged') => {
    const actionMap = {
      empty: 'capture_empty',
      good: 'capture_good',
      damaged: 'capture_damaged'
    };
    
    const labelMap = {
      empty: 'Sem Copo',
      good: 'Copo Bom',
      damaged: 'Copo Danificado'
    };

    sendCommand({ action: actionMap[type] });
    addLogMessage(`Capturando: ${labelMap[type]}`, 'INFO');
  };

  const determineDetectedState = useCallback(() => {
    const { sem_copo, copo_bom, copo_danificado } = data.valores;

    let detectedState: 'SEM_COPO' | 'COPO_BOM' | 'COPO_DANIFICADO' = 'SEM_COPO';
    let maxVal = sem_copo;

    if (copo_bom > maxVal) {
      maxVal = copo_bom;
      detectedState = 'COPO_BOM';
    }
    if (copo_danificado > maxVal) {
      maxVal = copo_danificado;
      detectedState = 'COPO_DANIFICADO';
    }

    return detectedState;
  }, [data.valores]);

  const currentDetectedState = determineDetectedState();

  const getEstadoBgClass = (estado: 'SEM_COPO' | 'COPO_BOM' | 'COPO_DANIFICADO') => {
    switch (estado) {
      case 'COPO_BOM': return 'bg-green-100 text-green-800';
      case 'COPO_DANIFICADO': return 'bg-red-100 text-red-800';
      case 'SEM_COPO': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getDetectionIcon = (estado: 'SEM_COPO' | 'COPO_BOM' | 'COPO_DANIFICADO') => {
    switch (estado) {
      case 'COPO_BOM': return <img src="/Com_Copo.svg" alt="Copo Bom" className="w-6 h-6 ml-2" />;
      case 'COPO_DANIFICADO': return <img src="/Copo_Danificado.svg" alt="Copo Danificado" className="w-6 h-6 ml-2" />;
      case 'SEM_COPO': return <img src="/Sem_Copo.svg" alt="Sem Copo" className="w-6 h-6 ml-2" />;
      default: return null;
    }
  };

  const videoFeedUrl = "http://localhost:5000/video_feed";

  useEffect(() => {
    if (data.status === 'DETECCAO' && data.treinamento_completo) {
      const stateMap = {
        'SEM_COPO': 'Sem Copo',
        'COPO_BOM': 'Copo Bom',
        'COPO_DANIFICADO': 'Copo Danificado'
      };

      if (currentDetectedState !== prevDetectedStateRef.current) {
        addLogMessage(`DETECÇÃO: ${stateMap[currentDetectedState].toUpperCase()} (S:${data.valores.sem_copo.toFixed(2)}, B:${data.valores.copo_bom.toFixed(2)}, D:${data.valores.copo_danificado.toFixed(2)})`, 'OK');

        if (data.plc.conectado && data.plc.db18_disponivel) {
          addLogMessage(`Sinal enviado ao PLC: ${stateMap[currentDetectedState]}`, 'INFO');
        }
        prevDetectedStateRef.current = currentDetectedState;
      }
    }
  }, [data.status, data.treinamento_completo, data.valores, data.plc.conectado, data.plc.db18_disponivel, currentDetectedState, addLogMessage]);

  return (
    <div className="relative min-h-screen bg-gray-100 text-gray-800 font-sans overflow-hidden">
      {/* Background AI Effect */}
      <div className="absolute inset-0 z-[-1] pointer-events-none">
        <style>
          {`
          .ai-bg-effect {
            width: 100%;
            height: 100%;
            background-image:
              radial-gradient(circle, rgba(0, 191, 255, 0.1) 1px, transparent 1px),
              linear-gradient(to right, rgba(0, 191, 255, 0.04) 1px, transparent 1px),
              linear-gradient(to bottom, rgba(0, 191, 255, 0.04) 1px, transparent 1px);
            background-size: 40px 40px, 40px 40px, 40px 40px;
            background-position: 0 0, 0 0, 0 0;
            animation: moveGrid 30s linear infinite;
            opacity: 0.3;
            filter: blur(0.5px);
          }

          @keyframes moveGrid {
            0% {
              background-position: 0 0, 0 0, 0 0;
            }
            100% {
              background-position: 80px 80px, 80px 80px, 80px 80px;
            }
          }
          `}
        </style>
        <div className="ai-bg-effect"></div>
      </div>

      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 py-4 relative z-10">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <div className="flex-shrink-0">
            <img src="/Logo_Danilo.svg" alt="Danilo Logo" className="h-10 w-auto" />
          </div>
          <div className="flex-grow text-center">
            <h1 className="text-2xl font-bold text-gray-900">Smart Detection</h1>
            <div className="mt-1 p-2 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-center">
              </div>
            </div>
          </div>
          <div className="flex-shrink-0">
            <span className="text-sm text-gray-500">v1.0 </span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-3 gap-8 relative z-10">

        {/* Coluna Principal - Câmera ao Vivo */}
        <div className="lg:col-span-2 space-y-8">

          {/* Câmera ao Vivo */}
          <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Câmera ao Vivo</h2>
            <div className="relative w-full overflow-hidden rounded-xl border border-gray-600 bg-gray-900" style={{ paddingBottom: '56.25%' }}>
              {!isVideoError ? (
                <img
                  src={videoFeedUrl}
                  alt="Video Stream from Camera"
                  className={`absolute inset-0 w-full h-full object-contain ${!isConnected ? 'grayscale' : ''} transition-all duration-500`}
                  onError={(e) => {
                    console.error("Erro ao carregar o feed de vídeo:", e);
                    setIsVideoError(true);
                    addLogMessage('Câmera Offline', 'ERROR');
                  }}
                  onLoad={() => {
                    if (isVideoError) {
                      setIsVideoError(false);
                      addLogMessage('Câmera Online', 'OK');
                    }
                  }}
                />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-white text-center p-4 bg-gray-950">
                  <Camera className="w-16 h-16 mb-4 text-red-400" />
                  <p className="text-xl font-semibold">Câmera Offline</p>
                  <p className="text-sm text-gray-400 mt-2">Verifique a conexão do servidor de vídeo.</p>
                </div>
              )}
            </div>
            <div className={`mt-4 px-4 py-2 rounded-lg flex items-center ${getEstadoBgClass(currentDetectedState)} transition-colors duration-300`}>
              <span className={`w-3 h-3 rounded-full mr-2 ${currentDetectedState === 'COPO_BOM' ? 'bg-green-500' : currentDetectedState === 'COPO_DANIFICADO' ? 'bg-red-500' : 'bg-gray-500'}`}></span>
              <span className="font-semibold text-sm">
                STATUS: {currentDetectedState.replace('_', ' ')} DETECTADO
              </span>
              {getDetectionIcon(currentDetectedState)}
            </div>
          </div>

          {/* Nova linha para os blocos de "Valores de Detecção" e "Treinamento" */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Valores de Detecção */}
            <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100">
              <div className="flex items-center mb-4">
                <h2 className="text-xl font-semibold text-gray-900">Diagnóstico de Detecção</h2>
                {getDetectionIcon(currentDetectedState)}
              </div>

              <div className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium text-gray-700">Sem Copo</span>
                    <span className="text-sm font-mono text-gray-800">
                      {data.valores.sem_copo.toFixed(3)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-gray-400 h-2 rounded-full transition-all duration-500 ease-out"
                      style={{ width: `${Math.min(data.valores.sem_copo * 100, 100)}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium text-gray-700">Copo Bom</span>
                    <span className="text-sm font-mono text-green-700">
                      {data.valores.copo_bom.toFixed(3)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-500 h-2 rounded-full transition-all duration-500 ease-out"
                      style={{ width: `${Math.min(data.valores.copo_bom * 100, 100)}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium text-gray-700">Danificado</span>
                    <span className="text-sm font-mono text-red-700">
                      {data.valores.copo_danificado.toFixed(3)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-red-500 h-2 rounded-full transition-all duration-500 ease-out"
                      style={{ width: `${Math.min(data.valores.copo_danificado * 100, 100)}%` }}
                    />
                  </div>
                </div>
                <div className="mt-4 text-sm font-semibold text-gray-700">
                  Decisão Final: <span className={`${currentDetectedState === 'COPO_BOM' ? 'text-green-600' : currentDetectedState === 'COPO_DANIFICADO' ? 'text-red-600' : 'text-gray-600'}`}>
                    {currentDetectedState.replace('_', ' ')} (Maior Valor)
                  </span>
                </div>
              </div>
            </div>

            {/* Treinamento */}
            <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">Treinamento</h2>
                <button
                  onClick={handleTreinar}
                  disabled={!isConnected}
                  className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  title="Treinar">
                  <Settings className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-700">Status</span>
                  <span className={`px-3 py-1 rounded-md text-sm font-semibold ${data.treinamento_completo ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}`}>
                    {data.treinamento_completo ? 'Completo' : 'Pendente'}
                  </span>
                </div>
                <p className="text-sm text-gray-500">{data.contadores.sem_copo + data.contadores.copo_bom + data.contadores.copo_danificado}/30 amostras</p>
              </div>
              
              {/* Cards de Progresso */}
              <div className="mt-4 grid grid-cols-3 gap-3">
                <div className="flex flex-col items-center p-3 bg-gray-50 rounded-xl border border-gray-200 shadow-md">
                  <div className="relative w-12 h-12 mb-2">
                    <svg className="w-12 h-12 transform -rotate-90" viewBox="0 0 36 36">
                      <path
                        className="text-gray-300"
                        stroke="currentColor"
                        strokeWidth="3"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      <path
                        className="text-gray-500"
                        stroke="currentColor"
                        strokeWidth="3"
                        fill="none"
                        strokeDasharray={`${(data.contadores.sem_copo / 10) * 100}, 100`}
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <img src="/Sem_Copo.svg" alt="Sem Copo Icon" className="w-5 h-5" />
                    </div>
                  </div>
                  <span className="text-xs font-medium text-gray-700">Sem Copo</span>
                  <span className="text-xs font-mono text-gray-600">{data.contadores.sem_copo}/10</span>
                </div>

                <div className="flex flex-col items-center p-3 bg-green-50 rounded-xl border border-green-200 shadow-md">
                  <div className="relative w-12 h-12 mb-2">
                    <svg className="w-12 h-12 transform -rotate-90" viewBox="0 0 36 36">
                      <path
                        className="text-green-300"
                        stroke="currentColor"
                        strokeWidth="3"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      <path
                        className="text-green-500"
                        stroke="currentColor"
                        strokeWidth="3"
                        fill="none"
                        strokeDasharray={`${(data.contadores.copo_bom / 10) * 100}, 100`}
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <img src="/Com_Copo.svg" alt="Copo Bom Icon" className="w-5 h-5" />
                    </div>
                  </div>
                  <span className="text-xs font-medium text-green-700">Copo Bom</span>
                  <span className="text-xs font-mono text-green-600">{data.contadores.copo_bom}/10</span>
                </div>

                <div className="flex flex-col items-center p-3 bg-red-50 rounded-xl border border-red-200 shadow-md">
                  <div className="relative w-12 h-12 mb-2">
                    <svg className="w-12 h-12 transform -rotate-90" viewBox="0 0 36 36">
                      <path
                        className="text-red-300"
                        stroke="currentColor"
                        strokeWidth="3"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      <path
                        className="text-red-500"
                        stroke="currentColor"
                        strokeWidth="3"
                        fill="none"
                        strokeDasharray={`${(data.contadores.copo_danificado / 10) * 100}, 100`}
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <img src="/Copo_Danificado.svg" alt="Copo Danificado Icon" className="w-5 h-5" />
                    </div>
                  </div>
                  <span className="text-xs font-medium text-red-700">Danificado</span>
                  <span className="text-xs font-mono text-red-600">{data.contadores.copo_danificado}/10</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Coluna Lateral */}
        <div className="space-y-8 flex flex-col">
          {/* Status dos Componentes */}
          <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Status dos Componentes</h2>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-2">
                  <Cpu className="w-5 h-5 text-gray-500" />
                  <span className="text-gray-700">PLC</span>
                </div>
                <span className={`px-3 py-1 rounded-md text-xs font-semibold ${data.plc.conectado ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                  {data.plc.conectado ? 'Online' : 'Offline'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-2">
                  <Database className="w-5 h-5 text-gray-500" />
                  <span className="text-gray-700">DB18</span>
                </div>
                <span className={`px-3 py-1 rounded-md text-xs font-semibold ${data.plc.db18_disponivel ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                  {data.plc.db18_disponivel ? 'Online' : 'Offline'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-2">
                  <Wifi className="w-5 h-5 text-gray-500" />
                  <span className="text-gray-700">WebSocket</span>
                </div>
                <span className={`px-3 py-1 rounded-md text-xs font-semibold ${isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                  {isConnected ? 'Online' : 'Offline'}
                </span>
              </div>
            </div>

            {/* Botões de Controle */}
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="flex justify-center space-x-4">
                <button
                  onClick={handleDetectar}
                  disabled={!isConnected || !data.treinamento_completo}
                  className="p-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  title="Detectar">
                  <PlayCircle className="w-5 h-5" />
                </button>
                
                <button
                  onClick={handleReset}
                  disabled={!isConnected}
                  className="p-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  title="Reset">
                  <RotateCcw className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>

          {/* Log de Eventos */}
          <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Log de Eventos</h2>
            <div className="space-y-1 overflow-y-auto custom-scrollbar" style={{ height: '518px' }}>
              {logMessages.length > 0 ? (
                logMessages.map((log, index) => {
                  let textColorClass = 'text-gray-600';
                  let prefixStyle = 'font-bold mr-1';

                  if (log.includes('[OK]')) {
                    textColorClass = 'text-green-600';
                  } else if (log.includes('[ALERTA]')) {
                    textColorClass = 'text-amber-600';
                  } else if (log.includes('[ERRO]')) {
                    textColorClass = 'text-red-600';
                  } else if (log.includes('[INFO]')) {
                    textColorClass = 'text-blue-600';
                  }

                  if (log.includes('DETECÇÃO:')) {
                    textColorClass = 'text-green-700 font-bold';
                    prefixStyle = 'font-extrabold mr-1';
                  }

                  const parts = log.match(/^>(.*?):(.*)/);
                  const formattedLog = parts ? (
                    <>
                      <span className={`${prefixStyle} ${textColorClass}`}>{parts[1]}:</span>
                      <span className={`${textColorClass}`}>{parts[2]}</span>
                    </>
                  ) : (
                    <span className={textColorClass}>{log}</span>
                  );

                  return (
                    <p key={index} className={`text-xs ${textColorClass}`}>
                      {formattedLog}
                    </p>
                  );
                })
              ) : (
                <p className="text-sm text-gray-500">Aguardando eventos...</p>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Modal de Treinamento Moderno */}
      <TrainingModal
        isOpen={showTrainingModal}
        onClose={() => setShowTrainingModal(false)}
        data={data}
        isConnected={isConnected}
        onCapture={handleCapture}
        videoFeedUrl={videoFeedUrl}
        isVideoError={isVideoError}
      />
    </div>
  );
};

export default Dashboard;