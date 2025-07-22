// 📊 SmartCounters Component - Contadores Inteligentes

import React from 'react';
import { CheckCircle, XCircle, BarChart3, TrendingUp } from 'lucide-react';
import StatusCard from '../ui/StatusCard';
import type { WebSocketData } from '../../types';

interface SmartCountersProps {
  data: WebSocketData;
}

export const SmartCounters: React.FC<SmartCountersProps> = ({ data }) => {
  const counters = data.contadores_inteligentes;
  
  if (!counters) return null;

  const approvalRate = counters.total_detections > 0 
    ? ((counters.copo_bom_count / counters.total_detections) * 100)
    : 0;

  const rejectionRate = counters.total_detections > 0 
    ? ((counters.copo_danificado_count / counters.total_detections) * 100)
    : 0;

  return (
    <StatusCard title="📊 Contadores de Produção">
      <div className="space-y-4">
        {/* Grid Principal */}
        <div className="grid grid-cols-3 gap-4">
          {/* Aprovados */}
          <div className="bg-green-50 p-4 rounded-lg border border-green-200">
            <div className="flex items-center justify-between mb-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <span className="text-xs text-green-700 font-medium">APROVADOS</span>
            </div>
            <div className="text-2xl font-bold text-green-700">
              {counters.copo_bom_count}
            </div>
            <div className="text-xs text-green-600 mt-1">
              {approvalRate.toFixed(1)}%
            </div>
          </div>

          {/* Rejeitados */}
          <div className="bg-red-50 p-4 rounded-lg border border-red-200">
            <div className="flex items-center justify-between mb-2">
              <XCircle className="w-5 h-5 text-red-600" />
              <span className="text-xs text-red-700 font-medium">REJEITADOS</span>
            </div>
            <div className="text-2xl font-bold text-red-700">
              {counters.copo_danificado_count}
            </div>
            <div className="text-xs text-red-600 mt-1">
              {rejectionRate.toFixed(1)}%
            </div>
          </div>

          {/* Total */}
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
            <div className="flex items-center justify-between mb-2">
              <BarChart3 className="w-5 h-5 text-blue-600" />
              <span className="text-xs text-blue-700 font-medium">TOTAL</span>
            </div>
            <div className="text-2xl font-bold text-blue-700">
              {counters.total_detections}
            </div>
            <div className="text-xs text-blue-600 mt-1">
              Processados
            </div>
          </div>
        </div>

        {/* Barra de Progresso */}
        {counters.total_detections > 0 && (
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-gray-700">Taxa de Qualidade</span>
              <TrendingUp className="w-4 h-4 text-gray-500" />
            </div>
            
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div className="flex h-3 rounded-full overflow-hidden">
                {/* Barra Verde - Aprovados */}
                <div 
                  className="bg-green-500 transition-all duration-300"
                  style={{ width: `${approvalRate}%` }}
                />
                {/* Barra Vermelha - Rejeitados */}
                <div 
                  className="bg-red-500 transition-all duration-300"
                  style={{ width: `${rejectionRate}%` }}
                />
              </div>
            </div>
            
            <div className="flex justify-between text-xs text-gray-600 mt-2">
              <span>✅ {counters.copo_bom_count} aprovados</span>
              <span>❌ {counters.copo_danificado_count} rejeitados</span>
            </div>
          </div>
        )}

        {/* Estado Atual */}
        <div className="bg-gray-50 p-3 rounded-lg">
          <div className="flex items-center justify-between">
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

        {/* Reset Info */}
        {counters.total_detections === 0 && (
          <div className="text-center py-4 text-gray-500">
            <BarChart3 className="w-8 h-8 mx-auto mb-2 text-gray-400" />
            <p className="text-sm">Nenhuma detecção registrada</p>
            <p className="text-xs text-gray-400">Inicie a detecção para ver os contadores</p>
          </div>
        )}
      </div>
    </StatusCard>
  );
};

export default SmartCounters;