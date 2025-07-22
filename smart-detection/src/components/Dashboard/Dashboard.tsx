// 📊 Dashboard Main Component - Smart Detection Dashboard

import React, { useState, useEffect, useRef } from 'react';

// Hooks
import { useWebSocket } from '../../hooks/useWebSocket';

// Components
import CameraFeed from './CameraFeed';
import DetectionValues from './DetectionValues';
import TrainingProgress from './TrainingProgress';
import SystemStatus from './SystemStatus';
import TrainingModal from '../TrainingModal/TrainingModal';
import { TrainingGallery } from '../../components/TrainingGallery';
import { Button } from '../ui/Button'; // Assuming Button component has good styles already

// Utils
import { determineDetectedState, getStateDisplayName } from '../../utils/helpers';
import { API_ENDPOINTS, WEBSOCKET_COMMANDS, LOG_TYPES } from '../../utils/constants';

// Types
import type { CaptureType, DetectionState } from '../../types';

const Dashboard: React.FC = () => {
    // WebSocket Hook
    const { data, isConnected, sendCommand, logMessages, addLogMessage } = useWebSocket(API_ENDPOINTS.WEBSOCKET);

    // State
    const [isVideoError, setIsVideoError] = useState(false);
    const [showTrainingModal, setShowTrainingModal] = useState(false);
    const [showGalleryModal, setShowGalleryModal] = useState(false);
    const prevDetectedStateRef = useRef<DetectionState | null>(null);

    // Handlers
    const handleTreinar = () => {
        setShowTrainingModal(true);
        sendCommand({ action: WEBSOCKET_COMMANDS.TRAIN });
        addLogMessage('Iniciando modo treinamento...', LOG_TYPES.INFO);
    };

    const handleDetectar = () => {
        if (data.treinamento_completo) {
            sendCommand({ action: WEBSOCKET_COMMANDS.DETECT });
            addLogMessage('Iniciando detecção...', LOG_TYPES.OK);
        } else {
            addLogMessage('Treinamento incompleto. Complete o treinamento primeiro.', LOG_TYPES.ALERT);
        }
    };

    const handleReset = () => {
        sendCommand({ action: WEBSOCKET_COMMANDS.RESET });
        addLogMessage('Resetando sistema...', LOG_TYPES.ALERT);
    };

    const handleCapture = (type: CaptureType) => {
        const actionMap = {
            empty: WEBSOCKET_COMMANDS.CAPTURE_EMPTY,
            good: WEBSOCKET_COMMANDS.CAPTURE_GOOD,
            damaged: WEBSOCKET_COMMANDS.CAPTURE_DAMAGED
        };
        
        const labelMap = {
            empty: 'Sem Copo',
            good: 'Copo Bom',
            damaged: 'Copo Danificado'
        };

        sendCommand({ action: actionMap[type] });
        addLogMessage(`Capturando: ${labelMap[type]}`, LOG_TYPES.INFO);
    };

    const handleVideoError = () => {
        setIsVideoError(true);
        addLogMessage('Câmera Offline', LOG_TYPES.ERROR);
    };

    const handleVideoLoad = () => {
        if (isVideoError) {
            setIsVideoError(false);
            addLogMessage('Câmera Online', LOG_TYPES.OK);
        }
    };

    const handleOpenGallery = () => {
        setShowGalleryModal(true);
        addLogMessage('Abrindo galeria de imagens de treinamento...', LOG_TYPES.INFO);
    };

    // Computed values
    const currentDetectedState = determineDetectedState(data.valores);

    // Effects
    useEffect(() => {
        if (data.status === 'DETECCAO' && data.treinamento_completo) {
            if (currentDetectedState !== prevDetectedStateRef.current) {
                const displayName = getStateDisplayName(currentDetectedState);
                addLogMessage(
                    `DETECÇÃO: ${displayName.toUpperCase()} (S:${data.valores.sem_copo.toFixed(2)}, B:${data.valores.copo_bom.toFixed(2)}, D:${data.valores.copo_danificado.toFixed(2)})`, 
                    LOG_TYPES.OK
                );

                if (data.plc?.conectado && data.plc?.db18_disponivel) { 
                    addLogMessage(`Sinal enviado ao PLC: ${displayName}`, LOG_TYPES.INFO);
                }
                
                prevDetectedStateRef.current = currentDetectedState;
            }
        }
    }, [data.status, data.treinamento_completo, data.valores, data.plc?.conectado, data.plc?.db18_disponivel, currentDetectedState, addLogMessage]);

    // Effect for logging smart counters (now focused on periodic production updates)
    useEffect(() => {
        const counters = data.contadores_inteligentes;
        if (counters && counters.total_detections > 0) {
            // Log when there's a new detection in counters and it's not 'SEM_COPO'
            if (data.estado_detectado && data.estado_detectado !== 'SEM_COPO') {
                const approval = counters.total_detections > 0 
                    ? ((counters.copo_bom_count / counters.total_detections) * 100).toFixed(1)
                    : '0';
                
                // Log every 5 detections
                if (counters.total_detections % 5 === 0) {
                    addLogMessage(
                        `📊 Produção: ${counters.total_detections} total, ${approval}% aprovação`, 
                        LOG_TYPES.INFO
                    );
                }
            }
        }
    }, [data.contadores_inteligentes, data.estado_detectado, addLogMessage]);


    return (
        <div className="relative min-h-screen bg-gray-50 text-gray-800 font-sans overflow-hidden">
            {/* Background AI Effect (Inline SVG) - Slightly more subtle */}
            <div className="absolute inset-0 z-[-1] pointer-events-none opacity-20"> {/* Changed opacity */}
                <svg width="100%" height="100%" viewBox="0 0 1440 810" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
                    <rect width="1440" height="810" fill="#F8FAFC"/> {/* Lighter background for the grid */}
                    <g>
                        {/* Horizontal Lines */}
                        <path d="M-100 50L1540 50M-100 150L1540 150M-100 250L1540 250M-100 350L1540 350M-100 450L1540 450M-100 550L1540 550M-100 650L1540 650M-100 750L1540 750" stroke="#00BFFF" strokeWidth="0.8"/> {/* Slightly thinner stroke */}
                        {/* Vertical Lines */}
                        <path d="M50 -100L50 910M150 -100L150 910M250 -100L250 910M350 -100L350 910M450 -100L450 910M550 -100L550 910M650 -100L650 910M750 -100L750 910M850 -100L850 910M950 -100L950 910M1050 -100L1050 910M1150 -100L1150 910M1250 -100L1250 910M1350 -100L1350 910" stroke="#00BFFF" strokeWidth="0.8"/> {/* Slightly thinner stroke */}
                        {/* Example Circles/Nodes */}
                        <circle cx="200" cy="200" r="4" fill="#00BFFF"/> {/* Smaller circles */}
                        <circle cx="400" cy="400" r="4" fill="#00BFFF"/>
                        <circle cx="600" cy="600" r="4" fill="#00BFFF"/>
                        <circle cx="800" cy="100" r="4" fill="#00BFFF"/>
                        <circle cx="1000" cy="300" r="4" fill="#00BFFF"/>
                        <circle cx="1200" cy="500" r="4" fill="#00BFFF"/>
                        <circle cx="100" cy="700" r="4" fill="#00BFFF"/>
                        
                        {/* More dynamic diagonal lines for tech feel */}
                        <line x1="0" y1="0" x2="1440" y2="810" stroke="#00BFFF" strokeWidth="0.4" /> {/* Thinner lines */}
                        <line x1="1440" y1="0" x2="0" y2="810" stroke="#00BFFF" strokeWidth="0.4" />
                        <line x1="300" y1="0" x2="1440" y2="500" stroke="#00BFFF" strokeWidth="0.4" />
                        <line x1="0" y1="300" x2="1140" y2="810" stroke="#00BFFF" strokeWidth="0.4" />
                        <line x1="50" y1="810" x2="1440" y2="10" stroke="#00BFFF" strokeWidth="0.4" />
                        <line x1="1390" y1="810" x2="0" y2="10" stroke="#00BFFF" strokeWidth="0.4" />

                        {/* Additional subtle paths for complexity */}
                        <path d="M100 0 C300 150, 50 400, 250 500 S 700 800, 900 750" stroke="#00BFFF" strokeWidth="0.1" fill="none"/> {/* Even thinner */}
                        <path d="M1440 100 C1200 250, 1400 500, 1200 600 S 800 850, 600 800" stroke="#00BFFF" strokeWidth="0.1" fill="none"/>
                    </g>
                </svg>
            </div>

            {/* Header */}
            <header className="bg-white shadow-md border-b border-gray-100 py-4 relative z-10"> {/* Changed shadow and border */}
                <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
                    <div className="flex-shrink-0">
                        <img src="/Logo_Danilo.svg" alt="Danilo Logo" className="h-10 w-auto" />
                    </div>
                    <div className="flex-grow text-center">
                        <h1 className="text-2xl font-bold text-gray-900">Smart Detection</h1>
                        <div className="mt-1 p-2 bg-gray-50 rounded-lg">
                            <div className="flex items-center justify-center">
                                {/* Pode adicionar um status geral ou um contador global aqui se desejar */}
                            </div>
                        </div>
                    </div>
                    <div className="flex-shrink-0">
                        <span className="text-sm text-gray-500">v1.0</span>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-6 py-10 grid grid-cols-1 lg:grid-cols-3 gap-10 relative z-10"> {/* Increased padding and gap */}
                {/* Main Column - Camera Feed & Detection/Training */}
                <div className="lg:col-span-2 space-y-10"> {/* Increased space-y */}
                    {/* Live Camera Feed */}
                    <CameraFeed
                        videoFeedUrl={API_ENDPOINTS.VIDEO_FEED}
                        isVideoError={isVideoError}
                        isConnected={isConnected}
                        currentDetectedState={currentDetectedState}
                        onVideoError={handleVideoError}
                        onVideoLoad={handleVideoLoad}
                    />

                    {/* Detection Values and Training Progress */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-10"> {/* Increased gap */}
                        <DetectionValues
                            data={data}
                            currentDetectedState={currentDetectedState}
                        />

                        <TrainingProgress
                            data={data}
                            isConnected={isConnected}
                            onStartTraining={handleTreinar}
                            onOpenGallery={handleOpenGallery} 
                        />
                    </div>
                </div>

                {/* Side Column - System Status, Counters, and Logs */}
                <SystemStatus
                    data={data}
                    isConnected={isConnected}
                    logMessages={logMessages}
                    onDetect={handleDetectar}
                    onReset={handleReset}
                />
            </main>

            {/* Training Modal */}
            <TrainingModal
                isOpen={showTrainingModal}
                onClose={() => setShowTrainingModal(false)}
                data={data}
                isConnected={isConnected}
                onCapture={handleCapture}
                videoFeedUrl={API_ENDPOINTS.VIDEO_FEED}
                isVideoError={isVideoError}
            />

            {/* Gallery Modal */}
            {showGalleryModal && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
                    onClick={() => setShowGalleryModal(false)}
                >
                    <div
                        className="bg-white rounded-xl p-8 max-w-7xl w-full max-h-[95vh] overflow-y-auto shadow-2xl" // Slightly rounded, more padding, stronger shadow
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex justify-between items-center mb-6 border-b pb-4"> {/* Increased margin/padding */}
                            <h2 className="text-2xl font-bold text-gray-800">Galeria de Imagens de Treinamento</h2>
                            <button
                                onClick={() => setShowGalleryModal(false)}
                                className="text-gray-500 hover:text-gray-700 text-4xl leading-none font-semibold transition-colors duration-200" // Larger, smoother transition
                            >
                                &times;
                            </button>
                        </div>
                        <TrainingGallery />
                        <div className="mt-8 flex justify-end"> {/* Increased margin */}
                            <Button
                                onClick={() => setShowGalleryModal(false)}
                                variant="secondary"
                                size="md"
                            >
                                Fechar
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Dashboard;