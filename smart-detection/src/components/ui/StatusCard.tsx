// 🔧 StatusCard Component - Smart Detection Dashboard

import React from 'react';

interface StatusCardProps {
  title: string;
  children: React.ReactNode;
  className?: string;
  icon?: React.ReactNode;
}

export const StatusCard: React.FC<StatusCardProps> = ({
  title,
  children,
  className = '',
  icon
}) => {
  return (
    <div className={`bg-white rounded-2xl shadow-xl p-6 border border-gray-100 ${className}`}>
      <div className="flex items-center mb-4">
        {icon && <div className="mr-2">{icon}</div>}
        <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
      </div>
      {children}
    </div>
  );
};

export default StatusCard;