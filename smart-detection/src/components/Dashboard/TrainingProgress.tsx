// 📊 TrainingProgress Component - Smart Detection Dashboard

import React from 'react';
import { Settings, Eye } from 'lucide-react'; // Importe o ícone Eye também
import StatusCard from '../ui/StatusCard';
import ProgressCircle from '../ui/ProgressCircle';
import Button from '../ui/Button';
import type { WebSocketData } from '../../types';

interface TrainingProgressProps {
  data: WebSocketData;
  isConnected: boolean;
  onStartTraining: () => void;
  onOpenGallery: () => void; // NOVO: Adicione esta prop para o botão da galeria
}

export const TrainingProgress: React.FC<TrainingProgressProps> = ({
  data,
  isConnected,
  onStartTraining,
  onOpenGallery // Receba a nova prop
}) => {
  const totalSamples = data.contadores.sem_copo + data.contadores.copo_bom + data.contadores.copo_danificado;

  return (
    <StatusCard 
      title="Treinamento"
      icon={
        // AGORA É UM DIV CONTENDO OS DOIS BOTÕES
        <div className="flex items-center space-x-2"> {/* Use flexbox para alinhar os botões */}
          <Button
            onClick={onStartTraining}
            disabled={!isConnected}
            variant="primary"
            size="sm"
            icon={<Settings />}
            title="Treinar"
          />
          <Button // NOVO BOTÃO: "Ver Imagens"
            onClick={onOpenGallery} // Chama a função passada via prop
            variant="secondary" // Use uma variante diferente para distinguir, se quiser
            size="sm"
            icon={<Eye />} // Ícone de olho
            title="Ver Imagens"
          />
        </div>
      }
    >
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <span className="text-gray-700">Status</span>
          <span className={`px-3 py-1 rounded-md text-sm font-semibold ${
            data.treinamento_completo ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'
          }`}>
            {data.treinamento_completo ? 'Completo' : 'Pendente'}
          </span>
        </div>
        <p className="text-sm text-gray-500">{totalSamples}/30 amostras</p>
      </div>
      
      {/* Cards de Progresso */}
      <div className="mt-4 grid grid-cols-3 gap-3">
        <div className="flex flex-col items-center p-3 bg-gray-50 rounded-xl border border-gray-200 shadow-md">
          <ProgressCircle
            progress={(data.contadores.sem_copo / 10) * 100}
            color="gray"
            size="md"
            icon={<img src="/Sem_Copo.svg" alt="Sem Copo Icon" className="w-5 h-5" />}
            showText={false}
            className="mb-2"
          />
          <span className="text-xs font-medium text-gray-700">Sem Copo</span>
          <span className="text-xs font-mono text-gray-600">{data.contadores.sem_copo}/10</span>
        </div>

        <div className="flex flex-col items-center p-3 bg-green-50 rounded-xl border border-green-200 shadow-md">
          <ProgressCircle
            progress={(data.contadores.copo_bom / 10) * 100}
            color="green"
            size="md"
            icon={<img src="/Com_Copo.svg" alt="Copo Bom Icon" className="w-5 h-5" />}
            showText={false}
            className="mb-2"
          />
          <span className="text-xs font-medium text-green-700">Copo Bom</span>
          <span className="text-xs font-mono text-green-600">{data.contadores.copo_bom}/10</span>
        </div>

        <div className="flex flex-col items-center p-3 bg-red-50 rounded-xl border border-red-200 shadow-md">
          <ProgressCircle
            progress={(data.contadores.copo_danificado / 10) * 100}
            color="red"
            size="md"
            icon={<img src="/Copo_Danificado.svg" alt="Copo Danificado Icon" className="w-5 h-5" />}
            showText={false}
            className="mb-2"
          />
          <span className="text-xs font-medium text-red-700">Danificado</span>
          <span className="text-xs font-mono text-red-600">{data.contadores.copo_danificado}/10</span>
        </div>
      </div>
    </StatusCard>
  );
};

export default TrainingProgress;