// 📊 Dashboard Main Component - Smart Detection Dashboard

import React, { useState, useEffect, useRef } from 'react';

// Hooks
import { useWebSocket } from '../../hooks/useWebSocket';

// Components
import CameraFeed from './CameraFeed';
import DetectionValues from './DetectionValues';
import TrainingProgress from './TrainingProgress'; // Caminho correto
import SystemStatus from './SystemStatus';
import TrainingModal from '../TrainingModal/TrainingModal';
import { TrainingGallery } from '../../components/TrainingGallery'; // Caminho correto para TrainingGallery
import { Button } from '../ui/Button'; // Importado para uso no modal da galeria

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
    const [showGalleryModal, setShowGalleryModal] = useState(false); // Estado para o modal da galeria
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

    // Handler para abrir o modal da galeria
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

                // Correção de segurança: usar optional chaining para plc
                if (data.plc?.conectado && data.plc?.db18_disponivel) { 
                    addLogMessage(`Sinal enviado ao PLC: ${displayName}`, LOG_TYPES.INFO);
                }
                
                prevDetectedStateRef.current = currentDetectedState;
            }
        }
    }, [data.status, data.treinamento_completo, data.valores, data.plc?.conectado, data.plc?.db18_disponivel, currentDetectedState, addLogMessage]);

    return (
        <div className="relative min-h-screen bg-gray-100 text-gray-800 font-sans overflow-hidden">
            {/* Background AI Effect */}
            <div className="absolute inset-0 z-[-1] pointer-events-none">
                <style>
                    {`
                    .ai-bg-effect {
                        width: 100%;
                        height: 100%;
                        background-image:
                            radial-gradient(circle, rgba(0, 191, 255, 0.1) 1px, transparent 1px),
                            linear-gradient(to right, rgba(0, 191, 255, 0.04) 1px, transparent 1px),
                            linear-gradient(to bottom, rgba(0, 191, 255, 0.04) 1px, transparent 1px);
                        background-size: 40px 40px, 40px 40px, 40px 40px;
                        background-position: 0 0, 0 0, 0 0;
                        animation: moveGrid 30s linear infinite;
                        opacity: 0.3;
                        filter: blur(0.5px);
                    }

                    @keyframes moveGrid {
                        0% {
                            background-position: 0 0, 0 0, 0 0;
                        }
                        100% {
                            background-position: 80px 80px, 80px 80px, 80px 80px;
                        }
                    }
                    `}
                </style>
                <div className="ai-bg-effect"></div>
            </div>

            {/* Header */}
            <header className="bg-white shadow-sm border-b border-gray-200 py-4 relative z-10">
                <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
                    <div className="flex-shrink-0">
                        <img src="/Logo_Danilo.svg" alt="Danilo Logo" className="h-10 w-auto" />
                    </div>
                    <div className="flex-grow text-center">
                        <h1 className="text-2xl font-bold text-gray-900">Smart Detection</h1>
                        <div className="mt-1 p-2 bg-gray-50 rounded-lg">
                            <div className="flex items-center justify-center">
                                {/* Status indicator can be added here */}
                            </div>
                        </div>
                    </div>
                    <div className="flex-shrink-0">
                        <span className="text-sm text-gray-500">v1.0</span>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-3 gap-8 relative z-10">
                {/* Coluna Principal - Câmera ao Vivo */}
                <div className="lg:col-span-2 space-y-8">
                    {/* Câmera ao Vivo */}
                    <CameraFeed
                        videoFeedUrl={API_ENDPOINTS.VIDEO_FEED}
                        isVideoError={isVideoError}
                        isConnected={isConnected}
                        currentDetectedState={currentDetectedState}
                        onVideoError={handleVideoError}
                        onVideoLoad={handleVideoLoad}
                    />

                    {/* Valores de Detecção e Treinamento */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <DetectionValues
                            data={data}
                            currentDetectedState={currentDetectedState}
                        />

                        {/* Passando a prop onOpenGallery para o TrainingProgress */}
                        <TrainingProgress
                            data={data}
                            isConnected={isConnected}
                            onStartTraining={handleTreinar}
                            onOpenGallery={handleOpenGallery} 
                        />
                    </div>
                    {/* O StatusCard "Gerenciamento de Imagens" foi removido daqui */}
                </div>

                {/* Coluna Lateral - Status e Logs */}
                <SystemStatus
                    data={data}
                    isConnected={isConnected}
                    logMessages={logMessages}
                    onDetect={handleDetectar}
                    onReset={handleReset}
                />
            </main>

            {/* Modal de Treinamento (existente) */}
            <TrainingModal
                isOpen={showTrainingModal}
                onClose={() => setShowTrainingModal(false)}
                data={data}
                isConnected={isConnected}
                onCapture={handleCapture}
                videoFeedUrl={API_ENDPOINTS.VIDEO_FEED}
                isVideoError={isVideoError}
            />

            {/* Modal para a Galeria de Imagens de Treinamento */}
            {showGalleryModal && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
                    onClick={() => setShowGalleryModal(false)} // Fecha ao clicar fora do conteúdo
                >
                    <div
                        className="bg-white rounded-lg p-6 max-w-7xl w-full max-h-[95vh] overflow-y-auto" // Aumentado o max-w e max-h
                        onClick={(e) => e.stopPropagation()} // Impede que cliques dentro do modal o fechem
                    >
                        <div className="flex justify-between items-center mb-4 border-b pb-3">
                            <h2 className="text-2xl font-bold text-gray-800">Galeria de Imagens de Treinamento</h2>
                            <button
                                onClick={() => setShowGalleryModal(false)}
                                className="text-gray-500 hover:text-gray-700 text-3xl leading-none font-semibold"
                            >
                                &times; {/* Ícone de 'X' para fechar */}
                            </button>
                        </div>
                        <TrainingGallery /> {/* Renderiza o componente da galeria aqui */}
                        <div className="mt-6 flex justify-end">
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