// 🔧 ProgressCircle Component - Smart Detection Dashboard

import React from 'react';

interface ProgressCircleProps {
  progress: number; // 0 to 100
  size?: 'sm' | 'md' | 'lg';
  color?: 'gray' | 'green' | 'red' | 'blue';
  icon?: React.ReactNode;
  showText?: boolean;
  current?: number;
  total?: number;
  className?: string;
}

export const ProgressCircle: React.FC<ProgressCircleProps> = ({
  progress,
  size = 'md',
  color = 'blue',
  icon,
  showText = true,
  current,
  total,
  className = ''
}) => {
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-24 h-24'
  };

  const colors = {
    gray: 'text-gray-500',
    green: 'text-green-500',
    red: 'text-red-500',
    blue: 'text-blue-500'
  };

  const textSizes = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-2xl'
  };

  return (
    <div className={`relative ${sizes[size]} ${className}`}>
      <svg className={`${sizes[size]} transform -rotate-90`} viewBox="0 0 36 36">
        <path
          className="text-gray-300"
          stroke="currentColor"
          strokeWidth="3"
          fill="none"
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
        />
        <path
          className={colors[color]}
          stroke="currentColor"
          strokeWidth="3"
          fill="none"
          strokeDasharray={`${progress}, 100`}
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
        />
      </svg>
      
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {icon ? (
          <div className="flex items-center justify-center">
            {icon}
          </div>
        ) : showText && (
          <>
            {current !== undefined && total !== undefined ? (
              <>
                <span className={`font-bold text-gray-800 ${textSizes[size]}`}>
                  {current}
                </span>
                <span className={`text-gray-600 ${size === 'lg' ? 'text-sm' : 'text-xs'}`}>
                  /{total}
                </span>
              </>
            ) : (
              <span className={`font-bold text-gray-800 ${textSizes[size]}`}>
                {Math.round(progress)}%
              </span>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ProgressCircle;