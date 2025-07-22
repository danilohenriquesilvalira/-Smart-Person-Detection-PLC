// 📊 DetectionValues Component - Smart Detection Dashboard

import React from 'react';
import StatusCard from '../ui/StatusCard';
import type { WebSocketData, DetectionState } from '../../types';

interface DetectionValuesProps {
  data: WebSocketData;
  currentDetectedState: DetectionState;
}

export const DetectionValues: React.FC<DetectionValuesProps> = ({
  data,
  currentDetectedState
}) => {
  const getDetectionIcon = (estado: DetectionState) => {
    switch (estado) {
      case 'COPO_BOM': return <img src="/Com_Copo.svg" alt="Copo Bom" className="w-6 h-6 ml-2" />;
      case 'COPO_DANIFICADO': return <img src="/Copo_Danificado.svg" alt="Copo Danificado" className="w-6 h-6 ml-2" />;
      case 'SEM_COPO': return <img src="/Sem_Copo.svg" alt="Sem Copo" className="w-6 h-6 ml-2" />;
      default: return null;
    }
  };

  return (
    <StatusCard 
      title="Diagnóstico de Detecção"
      icon={getDetectionIcon(currentDetectedState)}
    >
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
          Decisão Final: <span className={`${
            currentDetectedState === 'COPO_BOM' ? 'text-green-600' : 
            currentDetectedState === 'COPO_DANIFICADO' ? 'text-red-600' : 'text-gray-600'
          }`}>
            {currentDetectedState.replace('_', ' ')} (Maior Valor)
          </span>
        </div>
      </div>
    </StatusCard>
  );
};

export default DetectionValues;