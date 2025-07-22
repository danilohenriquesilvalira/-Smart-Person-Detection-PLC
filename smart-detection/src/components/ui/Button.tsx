// 🔧 Button Component - Smart Detection Dashboard

import React from 'react';

interface ButtonProps {
  children?: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  title?: string;
  loading?: boolean;
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  onClick,
  disabled = false,
  variant = 'primary',
  size = 'md',
  className = '',
  title,
  loading = false,
  icon
}) => {
  const baseClasses = 'inline-flex items-center justify-center font-medium transition-all duration-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    primary: 'bg-blue-500 hover:bg-blue-600 text-white focus:ring-blue-500',
    secondary: 'bg-gray-500 hover:bg-gray-600 text-white focus:ring-gray-500',
    success: 'bg-green-500 hover:bg-green-600 text-white focus:ring-green-500',
    danger: 'bg-red-500 hover:bg-red-600 text-white focus:ring-red-500',
    warning: 'bg-amber-500 hover:bg-amber-600 text-white focus:ring-amber-500'
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base'
  };

  const iconSizes = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6'
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`${baseClasses} ${variants[variant]} ${sizes[size]} ${className} ${
        loading ? 'cursor-wait' : ''
      }`}
      title={title}
    >
      {loading ? (
        <div className={`animate-spin rounded-full border-2 border-white border-opacity-30 border-t-white ${iconSizes[size]} mr-2`} />
      ) : icon ? (
        <div className={`${iconSizes[size]} ${children ? 'mr-2' : ''} flex items-center justify-center`}>{icon}</div>
      ) : null}
      {children}
    </button>
  );
};

export default Button;