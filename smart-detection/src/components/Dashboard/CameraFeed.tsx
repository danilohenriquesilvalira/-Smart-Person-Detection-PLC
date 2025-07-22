// 📊 CameraFeed Component - Smart Detection Dashboard

import React from 'react';
import { Camera } from 'lucide-react';
import StatusCard from '../ui/StatusCard';
import type { DetectionState } from '../../types';

interface CameraFeedProps {
  videoFeedUrl: string;
  isVideoError: boolean;
  isConnected: boolean;
  currentDetectedState: DetectionState;
  onVideoError: () => void;
  onVideoLoad: () => void;
}

export const CameraFeed: React.FC<CameraFeedProps> = ({
  videoFeedUrl,
  isVideoError,
  isConnected,
  currentDetectedState,
  onVideoError,
  onVideoLoad
}) => {
  const getEstadoBgClass = (estado: DetectionState) => {
    switch (estado) {
      case 'COPO_BOM': return 'bg-green-100 text-green-800';
      case 'COPO_DANIFICADO': return 'bg-red-100 text-red-800';
      case 'SEM_COPO': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getDetectionIcon = (estado: DetectionState) => {
    switch (estado) {
      case 'COPO_BOM': return <img src="/Com_Copo.svg" alt="Copo Bom" className="w-6 h-6 ml-2" />;
      case 'COPO_DANIFICADO': return <img src="/Copo_Danificado.svg" alt="Copo Danificado" className="w-6 h-6 ml-2" />;
      case 'SEM_COPO': return <img src="/Sem_Copo.svg" alt="Sem Copo" className="w-6 h-6 ml-2" />;
      default: return null;
    }
  };

  return (
    <StatusCard title="Câmera ao Vivo">
      <div 
        className="relative w-full overflow-hidden rounded-xl border border-gray-600 bg-gray-900" 
        style={{ paddingBottom: '56.25%' }}
      >
        {!isVideoError ? (
          <img
            src={videoFeedUrl}
            alt="Video Stream from Camera"
            className={`absolute inset-0 w-full h-full object-contain ${
              !isConnected ? 'grayscale' : ''
            } transition-all duration-500`}
            onError={(e) => {
              console.error("Erro ao carregar o feed de vídeo:", e);
              onVideoError();
            }}
            onLoad={() => {
              onVideoLoad();
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
        <span className={`w-3 h-3 rounded-full mr-2 ${
          currentDetectedState === 'COPO_BOM' ? 'bg-green-500' : 
          currentDetectedState === 'COPO_DANIFICADO' ? 'bg-red-500' : 'bg-gray-500'
        }`}></span>
        <span className="font-semibold text-sm">
          STATUS: {currentDetectedState.replace('_', ' ')} DETECTADO
        </span>
        {getDetectionIcon(currentDetectedState)}
      </div>
    </StatusCard>
  );
};

export default CameraFeed;