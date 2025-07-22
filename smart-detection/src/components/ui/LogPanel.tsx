// 🔧 LogPanel Component - Smart Detection Dashboard

import React from 'react';

interface LogPanelProps {
  logs: string[];
  height?: string;
  maxLogs?: number;
  className?: string;
}

export const LogPanel: React.FC<LogPanelProps> = ({
  logs,
  height = '518px',
  maxLogs = 10,
  className = ''
}) => {
  const getLogStyle = (log: string) => {
    let textColorClass = 'text-gray-600';
    let prefixStyle = 'font-bold mr-1';

    if (log.includes('[OK]')) {
      textColorClass = 'text-green-600';
    } else if (log.includes('[ALERTA]')) {
      textColorClass = 'text-amber-600';
    } else if (log.includes('[ERRO]')) {
      textColorClass = 'text-red-600';
    } else if (log.includes('[INFO]')) {
      textColorClass = 'text-blue-600';
    }

    if (log.includes('DETECÇÃO:')) {
      textColorClass = 'text-green-700 font-bold';
      prefixStyle = 'font-extrabold mr-1';
    }

    return { textColorClass, prefixStyle };
  };

  const formatLog = (log: string, index: number) => {
    const { textColorClass, prefixStyle } = getLogStyle(log);
    const parts = log.match(/^>(.*?):(.*)/);

    if (parts) {
      return (
        <p key={index} className={`text-xs ${textColorClass}`}>
          <span className={`${prefixStyle} ${textColorClass}`}>{parts[1]}:</span>
          <span className={textColorClass}>{parts[2]}</span>
        </p>
      );
    }

    return (
      <p key={index} className={`text-xs ${textColorClass}`}>
        {log}
      </p>
    );
  };

  return (
    <div
      className={`space-y-1 overflow-y-auto custom-scrollbar ${className}`}
      style={{ height }}
    >
      {logs.length > 0 ? (
        logs.slice(0, maxLogs).map(formatLog)
      ) : (
        <p className="text-sm text-gray-500">Aguardando eventos...</p>
      )}
    </div>
  );
};

export default LogPanel;