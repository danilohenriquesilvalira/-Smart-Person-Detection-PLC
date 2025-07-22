// 📊 SystemStatus Component - Smart Detection Dashboard

import React from 'react';
import { Cpu, Database, Wifi, PlayCircle, RotateCcw } from 'lucide-react';
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
          height="518px"
          maxLogs={10}
        />
      </StatusCard>
    </div>
  );
};

export default SystemStatus;