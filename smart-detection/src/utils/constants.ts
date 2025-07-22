// 🛠️ Constants - Smart Detection Dashboard

export const API_ENDPOINTS = {
  WEBSOCKET: 'ws://localhost:8765',
  VIDEO_FEED: 'http://localhost:5000/video_feed'
} as const;

export const TRAINING_TARGETS = {
  SEM_COPO: 10,
  COPO_BOM: 10,
  COPO_DANIFICADO: 10,
  TOTAL: 30
} as const;

export const DETECTION_STATES = {
  SEM_COPO: 'SEM_COPO',
  COPO_BOM: 'COPO_BOM',
  COPO_DANIFICADO: 'COPO_DANIFICADO'
} as const;

export const LOG_TYPES = {
  INFO: 'INFO',
  OK: 'OK',
  ALERT: 'ALERT',
  ERROR: 'ERROR',
  DEBUG: 'DEBUG'
} as const;

export const WEBSOCKET_COMMANDS = {
  TRAIN: 'train',
  DETECT: 'detect',
  RESET: 'reset',
  CAPTURE_EMPTY: 'capture_empty',
  CAPTURE_GOOD: 'capture_good',
  CAPTURE_DAMAGED: 'capture_damaged'
} as const;

export const RECONNECT_CONFIG = {
  INITIAL_DELAY: 1000,
  MAX_DELAY: 5000,
  DELAY_MULTIPLIER: 500
} as const;

export const UI_CONFIG = {
  MAX_LOG_MESSAGES: 10,
  LOG_PANEL_HEIGHT: '518px',
  CAMERA_ASPECT_RATIO: '56.25%' // 16:9
} as const;