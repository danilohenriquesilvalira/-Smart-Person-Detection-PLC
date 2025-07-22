// 🎯 TrainingModal Component - Smart Detection Dashboard

import React, { useState } from 'react';
import { XCircle, ArrowLeft, ArrowRight, Check, Camera, AlertCircle } from 'lucide-react';
import ProgressStepper from './ProgressStepper';
import TrainingStepComponent from './TrainingStep';
import Button from '../ui/Button';
import type { WebSocketData, CaptureType, TrainingStep } from '../../types';

interface TrainingModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: WebSocketData;
  isConnected: boolean;
  onCapture: (type: CaptureType) => void;
  videoFeedUrl: string;
  isVideoError: boolean;
}

export const TrainingModal: React.FC<TrainingModalProps> = ({
  isOpen,
  onClose,
  data,
  isConnected,
  onCapture,
  videoFeedUrl,
  isVideoError
}) => {
  const [currentStep, setCurrentStep] = useState(0);

  const steps: TrainingStep[] = [
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
      action: 'capture_empty'
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
      action: 'capture_good'
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
      action: 'capture_damaged'
    }
  ];

  const currentStepData = steps[currentStep];
  const isCurrentStepComplete = currentStepData.count >= currentStepData.target;
  const canGoNext = currentStep < steps.length - 1 && isCurrentStepComplete;
  const canGoPrevious = currentStep > 0;
  const isTrainingComplete = steps.every(step => step.count >= step.target);

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

  const totalSamples = data.contadores.sem_copo + data.contadores.copo_bom + data.contadores.copo_danificado;

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
          
          <ProgressStepper steps={steps} currentStep={currentStep} />
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
              <TrainingStepComponent
                step={currentStepData}
                isConnected={isConnected}
                onCapture={onCapture}
              />

              {/* Overall Progress */}
              <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-700">Progresso Geral</span>
                  <span className="text-sm font-mono text-gray-600">
                    {totalSamples}/30
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-blue-800 h-3 rounded-full transition-all duration-500"
                    style={{ width: `${(totalSamples / 30) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex justify-between items-center">
          <Button
            onClick={handlePrevious}
            disabled={!canGoPrevious}
            variant="secondary"
            size="sm"
            icon={<ArrowLeft />}
          >
            Anterior
          </Button>

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
            <Button
              onClick={handleFinish}
              variant="success"
              size="sm"
              icon={<Check />}
            >
              Finalizar
            </Button>
          ) : (
            <Button
              onClick={handleNext}
              disabled={!canGoNext}
              variant="primary"
              size="sm"
              icon={<ArrowRight />}
            >
              Próximo
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default TrainingModal;