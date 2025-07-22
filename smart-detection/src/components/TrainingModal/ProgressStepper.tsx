// 🎯 ProgressStepper Component - Smart Detection Dashboard

import React from 'react';
import { ArrowRight, Check } from 'lucide-react';
import type { TrainingStep } from '../../types';

interface ProgressStepperProps {
  steps: TrainingStep[];
  currentStep: number;
}

export const ProgressStepper: React.FC<ProgressStepperProps> = ({
  steps,
  currentStep
}) => {
  return (
    <div className="mt-6 flex items-center justify-between">
      {steps.map((step, index) => (
        <div key={step.id} className="flex items-center">
          <div className={`flex items-center justify-center w-12 h-12 rounded-full border-2 transition-all ${
            index === currentStep 
              ? 'bg-white text-blue-600 border-white' 
              : index < currentStep || step.count >= step.target
                ? 'bg-green-500 text-white border-green-500'
                : 'bg-transparent text-white border-white border-opacity-50'
          }`}>
            {step.count >= step.target ? (
              <Check className="w-6 h-6" />
            ) : (
              <img src={step.icon} alt={step.title} className="w-6 h-6" />
            )}
          </div>
          
          <div className="ml-3 hidden sm:block">
            <div className={`text-sm font-medium ${
              index === currentStep ? 'text-white' : 'text-blue-100'
            }`}>
              {step.title}
            </div>
            <div className="text-xs text-blue-100">
              {step.count}/{step.target} amostras
            </div>
          </div>
          
          {index < steps.length - 1 && (
            <ArrowRight className="w-4 h-4 text-blue-200 mx-4 hidden sm:block" />
          )}
        </div>
      ))}
    </div>
  );
};

export default ProgressStepper;