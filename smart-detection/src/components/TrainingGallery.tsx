// 🖼️ src/components/TrainingGallery.tsx - Galeria Simples e Rápida

import React, { useState } from 'react';
import { Trash2, Eye, Download, RefreshCw, X } from 'lucide-react';
import { useTrainingImages } from '../hooks/useTrainingImages';
import { Button } from './ui/Button';
import { StatusCard } from './ui/StatusCard';

export const TrainingGallery: React.FC = () => {
    const { images, stats, loading, error, refresh, deleteImage, clearCategory } = useTrainingImages();
    const [selectedCategory, setSelectedCategory] = useState<string>('all');
    const [viewImage, setViewImage] = useState<string | null>(null);

    const filteredImages = selectedCategory === 'all' 
        ? images 
        : images.filter(img => img.category === selectedCategory);

    const imagesByCategory = images.reduce((acc, img) => {
        if (!acc[img.category]) acc[img.category] = [];
        acc[img.category].push(img);
        return acc;
    }, {} as Record<string, typeof images>);

    const getCategoryDisplayName = (category: string) => {
        const names = {
            'sem_copo': 'Sem Copo',
            'copo_bom': 'Copo Bom', 
            'copo_danificado': 'Copo Danificado'
        };
        return names[category as keyof typeof names] || category;
    };

    const getCategoryColor = (category: string) => {
        const colors = {
            'sem_copo': 'bg-gray-100 text-gray-800',
            'copo_bom': 'bg-green-100 text-green-800',
            'copo_danificado': 'bg-red-100 text-red-800'
        };
        return colors[category as keyof typeof colors] || 'bg-blue-100 text-blue-800';
    };

    const handleDelete = async (category: string, filename: string) => {
        if (confirm(`Deletar ${filename}?`)) {
            await deleteImage(category, filename);
            setViewImage(null);
        }
    };

    const handleClear = async (category: string) => {
        if (confirm(`Limpar categoria ${getCategoryDisplayName(category)}?`)) {
            await clearCategory(category);
        }
    };

    if (loading) {
        return (
            <StatusCard title="Galeria">
                <div className="flex items-center justify-center py-8">
                    <RefreshCw className="animate-spin w-5 h-5 mr-2" />
                    <span>Carregando...</span>
                </div>
            </StatusCard>
        );
    }

    if (error) {
        return (
            <StatusCard title="Galeria">
                <div className="text-center py-6">
                    <p className="text-red-600 mb-3">❌ {error}</p>
                    <Button onClick={refresh} variant="primary" size="sm">
                        Tentar Novamente
                    </Button>
                </div>
            </StatusCard>
        );
    }

    return (
        <>
            <StatusCard title="Galeria de Treinamento">
                {/* Stats */}
                <div className="flex justify-between items-center mb-4">
                    <span className="text-sm">
                        {stats?.total_images || 0} imagens • {stats?.completion_percentage?.toFixed(0) || 0}% completo
                    </span>
                    <Button onClick={refresh} variant="secondary" size="sm" icon={<RefreshCw />}>
                        Atualizar
                    </Button>
                </div>

                {/* Filtros */}
                <div className="flex gap-2 mb-4">
                    <button
                        onClick={() => setSelectedCategory('all')}
                        className={`px-3 py-1 rounded text-sm ${
                            selectedCategory === 'all'
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-100 hover:bg-gray-200'
                        }`}
                    >
                        Todas ({images.length})
                    </button>
                    
                    {Object.entries(imagesByCategory).map(([category, categoryImages]) => (
                        <button
                            key={category}
                            onClick={() => setSelectedCategory(category)}
                            className={`px-3 py-1 rounded text-sm ${
                                selectedCategory === category
                                    ? 'bg-blue-500 text-white'
                                    : 'bg-gray-100 hover:bg-gray-200'
                            }`}
                        >
                            {getCategoryDisplayName(category)} ({categoryImages.length})
                        </button>
                    ))}
                </div>

                {/* Grid */}
                {filteredImages.length > 0 ? (
                    <div className="grid grid-cols-3 md:grid-cols-5 lg:grid-cols-8 gap-2">
                        {filteredImages.map((image) => (
                            <div
                                key={`${image.category}-${image.filename}`}
                                className="group relative bg-gray-100 rounded overflow-hidden aspect-square"
                            >
                                <img
                                    src={`http://localhost:5000/api/training/image/${image.category}/${image.filename}`}
                                    alt={image.filename}
                                    className="w-full h-full object-cover cursor-pointer hover:scale-105 transition-transform"
                                    onClick={() => setViewImage(`http://localhost:5000/api/training/image/${image.category}/${image.filename}`)}
                                    crossOrigin="anonymous"
                                    loading="lazy"
                                />
                                
                                {/* Badge */}
                                <div className={`absolute top-1 left-1 px-1 py-0.5 rounded text-xs ${getCategoryColor(image.category)}`}>
                                    {getCategoryDisplayName(image.category).charAt(0)}
                                </div>
                                
                                {/* Actions */}
                                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center gap-1 transition-opacity">
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            setViewImage(`http://localhost:5000/api/training/image/${image.category}/${image.filename}`);
                                        }}
                                        className="p-1 bg-white/20 rounded hover:bg-white/30"
                                        title="Ver"
                                    >
                                        <Eye className="w-3 h-3 text-white" />
                                    </button>
                                    
                                    <a
                                        href={`http://localhost:5000/api/training/image/${image.category}/${image.filename}`}
                                        download={image.filename}
                                        onClick={(e) => e.stopPropagation()}
                                        className="p-1 bg-white/20 rounded hover:bg-white/30"
                                        title="Download"
                                    >
                                        <Download className="w-3 h-3 text-white" />
                                    </a>
                                    
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDelete(image.category, image.filename);
                                        }}
                                        className="p-1 bg-red-500/80 rounded hover:bg-red-600"
                                        title="Deletar"
                                    >
                                        <Trash2 className="w-3 h-3 text-white" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-8 text-gray-500">
                        <p>📷 Nenhuma imagem</p>
                        <p className="text-sm">Use o treinamento para capturar</p>
                    </div>
                )}

                {/* Clear Category */}
                {selectedCategory !== 'all' && filteredImages.length > 0 && (
                    <div className="mt-4 pt-4 border-t">
                        <Button
                            onClick={() => handleClear(selectedCategory)}
                            variant="danger"
                            size="sm"
                            icon={<Trash2 />}
                        >
                            Limpar "{getCategoryDisplayName(selectedCategory)}"
                        </Button>
                    </div>
                )}
            </StatusCard>

            {/* Modal Simples */}
            {viewImage && (
                <div 
                    className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
                    onClick={() => setViewImage(null)}
                >
                    <div className="relative max-w-4xl max-h-full">
                        <button
                            onClick={() => setViewImage(null)}
                            className="absolute -top-10 right-0 text-white hover:text-gray-300"
                        >
                            <X className="w-6 h-6" />
                        </button>
                        
                        <img
                            src={viewImage}
                            alt="Visualização"
                            className="max-w-full max-h-full object-contain rounded"
                            onClick={(e) => e.stopPropagation()}
                        />
                        
                        <div className="absolute bottom-0 left-0 right-0 bg-black/50 p-2 rounded-b flex gap-2 justify-center">
                            <a
                                href={viewImage}
                                download
                                className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                                onClick={(e) => e.stopPropagation()}
                            >
                                Download
                            </a>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};