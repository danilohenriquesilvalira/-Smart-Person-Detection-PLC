// 🎯 TrainingStep Component - Smart Detection Dashboard

import React, { useState } from 'react';
import { Camera, Check, CheckCircle } from 'lucide-react';
import Button from '../ui/Button';
import ProgressCircle from '../ui/ProgressCircle';
import type { TrainingStep, CaptureType } from '../../types';

interface TrainingStepProps {
  step: TrainingStep;
  isConnected: boolean;
  onCapture: (type: CaptureType) => void;
}

export const TrainingStepComponent: React.FC<TrainingStepProps> = ({
  step,
  isConnected,
  onCapture
}) => {
  const [isCapturing, setIsCapturing] = useState(false);
  const isComplete = step.count >= step.target;

  const handleCapture = async () => {
    setIsCapturing(true);
    onCapture(step.id);
    
    // Simula um pequeno delay para feedback visual
    setTimeout(() => {
      setIsCapturing(false);
    }, 500);
  };

  return (
    <div className={`p-6 rounded-xl ${step.bgColor} ${step.borderColor} border`}>
      <div className="flex items-center mb-4">
        <img src={step.icon} alt={step.title} className="w-8 h-8 mr-3" />
        <h4 className="text-xl font-bold text-gray-900">{step.title}</h4>
      </div>
      
      <p className="text-gray-700 mb-6">{step.description}</p>
      
      {/* Progress Circle */}
      <div className="flex items-center justify-center mb-6">
        <ProgressCircle
          progress={(step.count / step.target) * 100}
          color={step.color}
          size="lg"
          current={step.count}
          total={step.target}
        />
      </div>

      {/* Capture Button */}
      <Button
        onClick={handleCapture}
        disabled={!isConnected || isComplete}
        loading={isCapturing}
        variant={step.color === 'gray' ? 'secondary' : step.color === 'green' ? 'success' : 'danger'}
        size="lg"
        className="w-full py-4"
        icon={isComplete ? <Check /> : <Camera />}
      >
        {isCapturing ? (
          'Capturando...'
        ) : isComplete ? (
          'Etapa Concluída'
        ) : (
          'Capturar Amostra'
        )}
      </Button>

      {isComplete && (
        <div className="mt-4 p-3 bg-green-100 border border-green-200 rounded-lg">
          <div className="flex items-center text-green-800">
            <CheckCircle className="w-5 h-5 mr-2" />
            <span className="text-sm font-medium">Etapa concluída com sucesso!</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default TrainingStepComponent;