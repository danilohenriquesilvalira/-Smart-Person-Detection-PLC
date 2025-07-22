// 🎣 useWebSocket Hook - Smart Detection Dashboard

import { useState, useEffect, useRef, useCallback } from 'react';
import type { WebSocketData, UseWebSocketReturn, WebSocketCommand, LogType } from '../types';

export const useWebSocket = (url: string = 'ws://localhost:8765'): UseWebSocketReturn => {
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

  const addLogMessage = useCallback((message: string, type: LogType = 'INFO') => {
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

  const sendCommand = useCallback((command: WebSocketCommand) => {
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

    // Cleanup previous connection
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
          
          // Validação e normalização dos dados
          const validatedData: WebSocketData = {
            timestamp: rawData.timestamp || Date.now() / 1000,
            status: rawData.status || "AGUARDANDO",
            valores: {
              sem_copo: rawData.valores?.sem_copo ?? 0.0,
              copo_bom: rawData.valores?.copo_bom ?? 0.0,
              copo_danificado: rawData.valores?.copo_danificado ?? 0.0
            },
            contadores: {
              sem_copo: rawData.contadores?.sem_copo ?? 0,
              copo_bom: rawData.contadores?.copo_bom ?? 0,
              copo_danificado: rawData.contadores?.copo_danificado ?? 0
            },
            sensibilidade: rawData.sensibilidade ?? 0.1,
            treinamento_completo: rawData.treinamento_completo ?? false,
            plc: {
              conectado: rawData.plc?.conectado ?? false,
              db18_disponivel: rawData.plc?.db18_disponivel ?? false
            },
            controles: {
              pode_treinar: rawData.controles?.pode_treinar ?? true,
              pode_detectar: rawData.controles?.pode_detectar ?? false,
              pode_capturar: rawData.controles?.pode_capturar ?? false,
              modo_treinamento: rawData.controles?.modo_treinamento ?? false
            }
          };
          
          setData(validatedData);
        } catch (e) {
          console.warn('⚠️ Erro ao parsear dados WebSocket:', e);
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

  return { 
    data, 
    isConnected, 
    attempts, 
    sendCommand, 
    logMessages, 
    addLogMessage 
  };
};