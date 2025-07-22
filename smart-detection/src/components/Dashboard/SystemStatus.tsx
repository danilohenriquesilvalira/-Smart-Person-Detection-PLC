// 📊 SystemStatus Component - Smart Detection Dashboard (ATUALIZADO)

import React from 'react';
import { Cpu, Database, Wifi, PlayCircle, RotateCcw, CheckCircle, XCircle } from 'lucide-react';
import StatusCard from '../ui/StatusCard';
import Button from '../ui/Button';
import LogPanel from '../ui/LogPanel';
import type { WebSocketData, ComponentStatus } from '../../types';

interface SystemStatusProps {
  data: WebSocketData;
  isConnected: boolean;
  logMessages: string[];
  onDetect: () => void;
  onReset: () => void;
}

export const SystemStatus: React.FC<SystemStatusProps> = ({
  data,
  isConnected,
  logMessages,
  onDetect,
  onReset
}) => {
  const components: ComponentStatus[] = [
    {
      name: 'plc',
      icon: Cpu,
      isOnline: data.plc.conectado,
      label: 'PLC'
    },
    {
      name: 'db18',
      icon: Database,
      isOnline: data.plc.db18_disponivel,
      label: 'DB18'
    },
    {
      name: 'websocket',
      icon: Wifi,
      isOnline: isConnected,
      label: 'WebSocket'
    }
  ];

  const counters = data.contadores_inteligentes;
  const hasCounters = counters && counters.total_detections > 0;

  const approvalRate = hasCounters 
    ? ((counters.copo_bom_count / counters.total_detections) * 100)
    : 0;

  return (
    <div className="space-y-8 flex flex-col">
      {/* Status dos Componentes */}
      <StatusCard title="Status dos Componentes">
        <div className="space-y-3">
          {components.map((component) => {
            const IconComponent = component.icon;
            return (
              <div key={component.name} className="flex justify-between items-center">
                <div className="flex items-center space-x-2">
                  <IconComponent className="w-5 h-5 text-gray-500" />
                  <span className="text-gray-700">{component.label}</span>
                </div>
                <span className={`px-3 py-1 rounded-md text-xs font-semibold ${
                  component.isOnline
                     ? 'bg-green-100 text-green-800'
                     : 'bg-red-100 text-red-800'
                }`}>
                  {component.isOnline ? 'Online' : 'Offline'}
                </span>
              </div>
            );
          })}
        </div>

        {/* Contadores Rápidos */}
        {hasCounters && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center">
                <div className="flex items-center justify-center mb-1">
                  <CheckCircle className="w-4 h-4 text-green-600 mr-1" />
                  <span className="text-lg font-bold text-green-600">{counters.copo_bom_count}</span>
                </div>
                <div className="text-xs text-gray-500">Aprovados</div>
              </div>
              
              <div className="text-center">
                <div className="flex items-center justify-center mb-1">
                  <XCircle className="w-4 h-4 text-red-600 mr-1" />
                  <span className="text-lg font-bold text-red-600">{counters.copo_danificado_count}</span>
                </div>
                <div className="text-xs text-gray-500">Rejeitados</div>
              </div>

              <div className="text-center">
                <div className="text-lg font-bold text-blue-600">{counters.total_detections}</div>
                <div className="text-xs text-gray-500">Total</div>
              </div>
            </div>

            {/* Mini Barra de Taxa */}
            <div className="mt-3">
              <div className="text-center text-xs text-gray-600 mb-1">
                Taxa de Aprovação: {approvalRate.toFixed(1)}%
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-green-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${approvalRate}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Estado Atual */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex justify-between items-center mb-3">
            <span className="text-sm font-medium text-gray-700">Estado Atual:</span>
            <span className={`px-2 py-1 rounded text-xs font-semibold ${
              data.estado_detectado === 'COPO_BOM' 
                ? 'bg-green-100 text-green-800'
                : data.estado_detectado === 'COPO_DANIFICADO'
                ? 'bg-red-100 text-red-800'
                : 'bg-gray-100 text-gray-800'
            }`}>
              {data.estado_detectado === 'COPO_BOM' && '✅ APROVADO'}
              {data.estado_detectado === 'COPO_DANIFICADO' && '❌ REJEITADO'}
              {data.estado_detectado === 'SEM_COPO' && '⚪ AGUARDANDO'}
            </span>
          </div>
        </div>

        {/* Botões de Controle */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex justify-center space-x-4">
            <Button
              onClick={onDetect}
              disabled={!isConnected || !data.treinamento_completo}
              variant="success"
              size="sm"
              icon={<PlayCircle />}
              title="Detectar"
            />
                     
            <Button
              onClick={onReset}
              disabled={!isConnected}
              variant="danger"
              size="sm"
              icon={<RotateCcw />}
              title="Reset"
            />
          </div>
        </div>
      </StatusCard>

      {/* Log de Eventos */}
      <StatusCard title="Log de Eventos">
        <LogPanel 
          logs={logMessages}
          height="340px"
          maxLogs={10}
        />
      </StatusCard>
    </div>
  );
};

export default SystemStatus;