import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  // Camera, // Removed as it's not used
  Wifi,
  Settings,
  Play,
  Cpu,
  Database,
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
}

// Hook WebSocket
const useWebSocket = (url: string = 'ws://localhost:8765') => {
  const [data, setData] = useState<WebSocketData>({
    timestamp: Date.now() / 1000,
    status: "AGUARDANDO",
    valores: { sem_copo: 0.0, copo_bom: 0.0, copo_danificado: 0.0 },
    contadores: { sem_copo: 0, copo_bom: 0, copo_danificado: 0 },
    sensibilidade: 0.1,
    treinamento_completo: false,
    plc: { conectado: false, db18_disponivel: false }
  });

  const [isConnected, setIsConnected] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const [logMessages, setLogMessages] = useState<string[]>([]); // State for log messages

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
      return newLogs.slice(0, 10); // Manter as últimas 10 mensagens para um log mais compacto
    });
  }, []);

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
      addLogMessage(`Tentando conectar ao WebSocket em ${url}...`, 'INFO');

      wsRef.current.onopen = () => {
        if (!mountedRef.current) return;
        setIsConnected(true);
        setAttempts(0);
        addLogMessage('Conexão WebSocket estabelecida.', 'OK');
      };

      wsRef.current.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const rawData: WebSocketData = JSON.parse(event.data);
          if (rawData.valores) {
            setData(rawData);
          } else {
            console.warn("Dados do WebSocket não contêm a propriedade 'valores'.");
            addLogMessage("Dados do WebSocket não contêm a propriedade 'valores'.", 'ALERT');
          }
        } catch (e) {
          console.warn('Erro no JSON:', e);
          addLogMessage(`Erro ao parsear JSON do WebSocket: ${e}`, 'ERROR');
        }
      };

      wsRef.current.onclose = () => {
        if (!mountedRef.current) return;
        setIsConnected(false);
        addLogMessage('Conexão WebSocket fechada.', 'INFO');

        const delay = Math.min(1000 + (attempts * 500), 5000);
        reconnectRef.current = setTimeout(() => {
          if (mountedRef.current) {
            setAttempts(prev => prev + 1);
            addLogMessage(`Tentando reconectar em ${delay / 1000}s (Tentativa ${attempts + 1})...`, 'INFO');
            connect();
          }
        }, delay);
      };

      wsRef.current.onerror = (event) => {
        if (!mountedRef.current) return;
        setIsConnected(false);
        console.error('WebSocket Error:', event);
        addLogMessage(`Erro no WebSocket.`, 'ERROR');
      };

    } catch (e) {
      if (mountedRef.current) {
        addLogMessage(`Falha ao iniciar WebSocket: ${e}`, 'ERROR');
        reconnectRef.current = setTimeout(() => {
          if (mountedRef.current) {
            setAttempts(prev => prev + 1);
            connect();
          }
        }, 2000);
      }
    }
  }, [url, attempts, addLogMessage]);

  const sendCommand = useCallback((command: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        const commandString = JSON.stringify(command);
        wsRef.current.send(commandString);
        addLogMessage(`Comando enviado: ${commandString}`, 'INFO');
      } catch (e) {
        console.error('Erro enviando comando:', e);
        addLogMessage(`Erro enviando comando: ${e}`, 'ERROR');
      }
    } else {
      console.warn('WebSocket não está aberto. Não foi possível enviar o comando.');
      addLogMessage('WebSocket não está aberto. Não foi possível enviar o comando.', 'ALERT');
    }
  }, [addLogMessage]);

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

  // Keeping sendCommand in the return for potential future use, 
  // but if it's never used, you can remove it from here and the destructuring in Dashboard.
  return { data, isConnected, attempts, sendCommand, logMessages, addLogMessage }; 
};

// Dashboard Principal
const Dashboard: React.FC = () => {
  // Removed sendCommand from destructuring if not used
  const { data, isConnected, logMessages, addLogMessage } = useWebSocket(); 

  const prevDetectedStateRef = useRef<'SEM_COPO' | 'COPO_BOM' | 'COPO_DANIFICADO' | null>(null);
  const [isVideoError, setIsVideoError] = useState(false);

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

  // Modified to use SVG images
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
        addLogMessage(`STATUS: ${stateMap[currentDetectedState].toUpperCase()} DETECTADO (S:${data.valores.sem_copo.toFixed(2)}, B:${data.valores.copo_bom.toFixed(2)}, D:${data.valores.copo_danificado.toFixed(2)})`, 'INFO');

        if (data.plc.conectado && data.plc.db18_disponivel) {
          addLogMessage(`Enviado sinal de '${stateMap[currentDetectedState]}' para o PLC.`, 'INFO');
        } else {
          addLogMessage('PLC ou DB18 não conectados, sinal não enviado.', 'ALERT');
        }
        prevDetectedStateRef.current = currentDetectedState;
      }
    } else if (data.status === 'TREINAMENTO' && data.treinamento_completo === false) {
      if (prevDetectedStateRef.current !== null) {
        prevDetectedStateRef.current = null;
      }
      addLogMessage('Iniciando Treinamento...', 'INFO');
    } else if (data.status === 'AGUARDANDO' && data.treinamento_completo) {
      if (prevDetectedStateRef.current !== null) {
        prevDetectedStateRef.current = null;
      }
      addLogMessage('Treinamento completo. Sistema aguardando comandos.', 'OK');
    } else if (data.status === 'AGUARDANDO' && !data.treinamento_completo) {
      if (prevDetectedStateRef.current !== null) {
        prevDetectedStateRef.current = null;
      }
      addLogMessage('Sistema inicializado. Treinamento pendente.', 'INFO');
    }
  }, [data.status, data.treinamento_completo, data.valores, data.plc.conectado, data.plc.db18_disponivel, currentDetectedState, addLogMessage]);


  return (
    <div className="relative min-h-screen bg-gray-100 text-gray-800 font-sans overflow-hidden">
      {/* AI Technology Lines Background */}
      <div className="absolute inset-0 z-[-1] pointer-events-none">
        {/* Removed 'jsx' prop from the style tag */}
        <style>
          {`
          .ai-bg-effect {
            width: 100%;
            height: 100%;
            background-image:
              radial-gradient(circle, rgba(0, 191, 255, 0.1) 1px, transparent 1px), /* Subtle dots */
              linear-gradient(to right, rgba(0, 191, 255, 0.04) 1px, transparent 1px), /* Vertical lines */
              linear-gradient(to bottom, rgba(0, 191, 255, 0.04) 1px, transparent 1px); /* Horizontal lines */
            background-size: 40px 40px, 40px 40px, 40px 40px; /* Spacing of lines and dots */
            background-position: 0 0, 0 0, 0 0;
            animation: moveGrid 30s linear infinite; /* Increased duration for slower, smoother movement */
            opacity: 0.3; /* Overall subtlety */
            filter: blur(0.5px); /* Soften the lines */
          }

          @keyframes moveGrid {
            0% {
              background-position: 0 0, 0 0, 0 0;
            }
            100% {
              background-position: 80px 80px, 80px 80px, 80px 80px; /* Shifts the pattern further */
            }
          }
          `}
        </style>
        <div className="ai-bg-effect"></div>
      </div>

      {/* Header Simplificado */}
      <header className="bg-white shadow-sm border-b border-gray-200 py-4 relative z-10">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          {/* Logo */}
          <div className="flex-shrink-0">
            <img src="/Logo_Danilo.svg" alt="Danilo Logo" className="h-10 w-auto" />
          </div>

          {/* Título Centralizado */}
          <div className="flex-grow text-center">
            <h1 className="text-2xl font-bold text-gray-900">Painel de Controle - Detector de Copos</h1>
          </div>

          {/* Versão */}
          <div className="flex-shrink-0">
            <span className="text-sm text-gray-500">v1.0</span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-3 gap-8 relative z-10">

        {/* Coluna Principal (2/3 da largura em telas grandes) */}
        <div className="lg:col-span-2 space-y-8">

          {/* Câmera ao Vivo */}
          {/* Changed styling for a more modern look */}
          <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100 hover:shadow-2xl transition-all duration-300">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Câmera ao Vivo</h2>
            {/* Container for video feed with fixed aspect ratio */}
            <div className="relative w-full overflow-hidden rounded-xl border border-gray-600 bg-gray-900" style={{ paddingBottom: '56.25%' }}> {/* 16:9 Aspect Ratio */}
              {!isVideoError ? (
                <img
                  src={videoFeedUrl}
                  alt="Video Stream from Camera"
                  className={`absolute inset-0 w-full h-full object-contain ${!isConnected ? 'grayscale' : ''} transition-all duration-500`}
                  onError={(e) => {
                    console.error("Erro ao carregar o feed de vídeo:", e);
                    setIsVideoError(true);
                    addLogMessage('Câmera Offline: Verifique o servidor de vídeo.', 'ERROR');
                  }}
                  onLoad={() => {
                    if (isVideoError) {
                      setIsVideoError(false);
                      addLogMessage('Câmera Online.', 'OK');
                    }
                  }}
                />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-white text-center p-4 bg-gray-950">
                  <svg className="w-16 h-16 mb-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.7 10.3c-.6-.6-1.5-.9-2.4-.9h-.6c-1.5 0-2.8.6-3.7 1.6-1.1 1.2-1.7 2.8-1.7 4.5 0 1.2.3 2.3.9 3.2m8.3-8.3c.6.6.9 1.5.9 2.4v.6c0 1.5-.6 2.8-1.6 3.7-1.2 1.1-2.8 1.7-4.5 1.7-1.2 0-2.3-.3-3.2-.9m11.2-11.2a1 1 0 011.4 0l2 2a1 1 0 010 1.4L18.4 12l2.8 2.8a1 1 0 010 1.4l-2 2a1 1 0 01-1.4 0L12 18.4l-2.8 2.8a1 1 0 01-1.4 0l-2-2a1 1 0 010-1.4L5.6 12l-2.8-2.8a1 1 0 010-1.4l2-2a1 1 0 011.4 0L12 5.6l2.8-2.8a1 1 0 011.4 0z"></path></svg>
                  <p className="text-xl font-semibold">Câmera Offline</p>
                  <p className="text-sm text-gray-400 mt-2">Verifique a conexão do servidor de vídeo.</p>
                </div>
              )}
              {!isConnected && !isVideoError && (
                <div className="absolute inset-0 bg-black bg-opacity-70 flex flex-col items-center justify-center text-white text-center">
                  <Play className="w-12 h-12 mb-4 animate-bounce text-gray-400" />
                  <p className="text-xl font-semibold">Aguardando Conexão da Câmera...</p>
                  <p className="text-sm text-gray-400 mt-2">Pode levar alguns segundos.</p>
                </div>
              )}
            </div>
            {/* Status na parte inferior do video */}
            {/* Changed styling for a more modern look */}
            <div className={`mt-4 px-4 py-2 rounded-lg flex items-center ${getEstadoBgClass(currentDetectedState)} transition-colors duration-300`}>
              <span className={`w-3 h-3 rounded-full mr-2 ${currentDetectedState === 'COPO_BOM' ? 'bg-green-500' : currentDetectedState === 'COPO_DANIFICADO' ? 'bg-red-500' : 'bg-gray-500'}`}></span>
              <span className="font-semibold text-sm">
                STATUS: {currentDetectedState.replace('_', ' ')} DETECTADO
              </span>
            </div>
          </div>

          {/* Valores de Detecção / Diagnóstico de Detecção */}
          {/* Changed styling for a more modern look */}
          <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100 hover:shadow-2xl transition-all duration-300">
            {/* Título com o ícone ao lado */}
            <div className="flex items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Diagnóstico de Detecção</h2>
              {getDetectionIcon(currentDetectedState)} {/* Ícone dinâmico aqui */}
            </div>

            <div className="space-y-4">
              {/* Sem Copo */}
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

              {/* Copo Bom */}
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

              {/* Copo Danificado */}
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
              {/* Decisão Final */}
              <div className="mt-4 text-sm font-semibold text-gray-700">
                Decisão Final: <span className={`${currentDetectedState === 'COPO_BOM' ? 'text-green-600' : currentDetectedState === 'COPO_DANIFICADO' ? 'text-red-600' : 'text-gray-600'}`}>
                  {currentDetectedState.replace('_', ' ')} (Maior Valor)
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Coluna Lateral (1/3 da largura em telas grandes) */}
        <div className="space-y-8 flex flex-col"> {/* Added flex flex-col here */}
          {/* Status dos Componentes (novo bloco) */}
          {/* Changed styling for a more modern look */}
          <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100 hover:shadow-2xl transition-all duration-300">
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
          </div>

          {/* Log de Eventos Recentes (novo posicionamento e estilo) */}
          {/* Changed styling for a more modern look */}
          <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100 hover:shadow-2xl transition-all duration-300">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Log de Eventos</h2>
            <div className="space-y-1 h-48 overflow-y-auto custom-scrollbar"> {/* Altura ajustada para ser mais compacto */}
              {logMessages.length > 0 ? (
                logMessages.map((log, index) => {
                  let textColorClass = 'text-gray-600'; // Cor padrão para logs
                  let prefixStyle = 'font-bold mr-1'; // Estilo para o prefixo

                  if (log.includes('[OK]')) {
                    textColorClass = 'text-green-600';
                  } else if (log.includes('[ALERTA]')) {
                    textColorClass = 'text-amber-600';
                  } else if (log.includes('[ERRO]')) {
                    textColorClass = 'text-red-600';
                  } else if (log.includes('[INFO]')) {
                    textColorClass = 'text-blue-600';
                  }

                  // Destaque para status de detecção
                  if (log.includes('STATUS: COPO BOM DETECTADO')) {
                    textColorClass = 'text-green-700 font-bold';
                    prefixStyle = 'font-extrabold mr-1'; // Extra bold for detected status
                  } else if (log.includes('STATUS: COPO DANIFICADO DETECTADO')) {
                    textColorClass = 'text-red-700 font-bold';
                    prefixStyle = 'font-extrabold mr-1';
                  } else if (log.includes('STATUS: SEM COPO DETECTADO')) {
                    textColorClass = 'text-gray-700 font-bold';
                    prefixStyle = 'font-extrabold mr-1';
                  }

                  // Split log message to style prefix and message separately
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
                    <p key={index} className={`text-xs ${textColorClass}`}> {/* Tamanho da fonte menor */}
                      {formattedLog}
                    </p>
                  );
                })
              ) : (
                <p className="text-sm text-gray-500">Nenhum evento recente.</p>
              )}
            </div>
          </div>

          {/* Treinamento / Captura de Treinamento */}
          {/* Changed styling for a more modern look */}
          <div className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100 flex-grow hover:shadow-2xl transition-all duration-300"> {/* Added flex-grow */}
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Treinamento</h2>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-700">Treinamento</span>
                <span className={`px-3 py-1 rounded-md text-sm font-semibold ${data.treinamento_completo ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}`}>
                  {data.treinamento_completo ? 'Completo' : 'Pendente'}
                </span>
                <Settings className="w-5 h-5 text-gray-500" />
              </div>
              <p className="text-sm text-gray-500">{data.contadores.sem_copo + data.contadores.copo_bom + data.contadores.copo_danificado}/30 amostras</p>
            </div>
            {/* Cards de Progresso de Treinamento */}
            <div className="mt-4 grid grid-cols-3 gap-3">
              {/* Sem Copo */}
              {/* Changed styling for a more modern look */}
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
                    <img src="/Sem_Copo.svg" alt="Sem Copo Icon" className="w-5 h-5" /> {/* Replaced MinusCircle */}
                  </div>
                </div>
                <span className="text-xs font-medium text-gray-700">Sem Copo</span>
                <span className="text-xs font-mono text-gray-600">{data.contadores.sem_copo}/10</span>
              </div>

              {/* Copo Bom */}
              {/* Changed styling for a more modern look */}
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
                    <img src="/Com_Copo.svg" alt="Copo Bom Icon" className="w-5 h-5" /> {/* Replaced CheckCircle */}
                  </div>
                </div>
                <span className="text-xs font-medium text-green-700">Copo Bom</span>
                <span className="text-xs font-mono text-green-600">{data.contadores.copo_bom}/10</span>
              </div>

              {/* Danificado */}
              {/* Changed styling for a more modern look */}
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
                    <img src="/Copo_Danificado.svg" alt="Copo Danificado Icon" className="w-5 h-5" /> {/* Replaced XCircle */}
                  </div>
                </div>
                <span className="text-xs font-medium text-red-700">Danificado</span>
                <span className="text-xs font-mono text-red-600">{data.contadores.copo_danificado}/10</span>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;