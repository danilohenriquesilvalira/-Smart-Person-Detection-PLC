// 🖼️ src/components/TrainingGallery.tsx - Galeria de Imagens

import React, { useState } from 'react';
import { Trash2, Eye, Download, RefreshCw } from 'lucide-react';
import { useTrainingImages } from '../hooks/useTrainingImages'; // Presumo que este hook está fazendo a requisição correta
import { Button } from './ui/Button';
import { StatusCard } from './ui/StatusCard';

export const TrainingGallery: React.FC = () => {
    // Este hook (useTrainingImages) é crucial. Ele deve estar buscando os dados da API corretamente.
    const { images, stats, loading, error, refresh, deleteImage, clearCategory } = useTrainingImages();
    const [selectedCategory, setSelectedCategory] = useState<string>('all');
    const [selectedImage, setSelectedImage] = useState<string | null>(null);

    // Filtrar imagens por categoria
    const filteredImages = selectedCategory === 'all' 
        ? images 
        : images.filter(img => img.category === selectedCategory);

    // Agrupar por categoria para os botões de filtro
    const imagesByCategory = images.reduce((acc, img) => {
        if (!acc[img.category]) acc[img.category] = [];
        acc[img.category].push(img);
        return acc;
    }, {} as Record<string, typeof images>);

    // Mapeamento para nomes de exibição (já está correto)
    const getCategoryDisplayName = (category: string) => {
        const names = {
            'sem_copo': 'Sem Copo',
            'copo_bom': 'Copo Bom', 
            'copo_danificado': 'Copo Danificado'
        };
        return names[category as keyof typeof names] || category;
    };

    // Mapeamento para cores de exibição (já está correto)
    const getCategoryColor = (category: string) => {
        const colors = {
            'sem_copo': 'bg-gray-100 text-gray-800',
            'copo_bom': 'bg-green-100 text-green-800',
            'copo_danificado': 'bg-red-100 text-red-800'
        };
        return colors[category as keyof typeof colors] || 'bg-blue-100 text-blue-800';
    };

    const handleDeleteImage = async (category: string, filename: string) => {
        if (confirm(`Deseja deletar a imagem ${filename}?`)) {
            const success = await deleteImage(category, filename);
            if (success) {
                alert('Imagem deletada com sucesso!');
            }
        }
    };

    const handleClearCategory = async (category: string) => {
        if (confirm(`Deseja limpar todas as imagens da categoria ${getCategoryDisplayName(category)}?`)) {
            const deletedCount = await clearCategory(category);
            if (deletedCount > 0) {
                alert(`${deletedCount} imagens removidas!`);
            }
        }
    };

    if (loading) {
        return (
            <StatusCard title="Galeria de Treinamento">
                <div className="flex items-center justify-center py-8">
                    <RefreshCw className="animate-spin w-6 h-6 mr-2" />
                    <span>Carregando imagens...</span>
                </div>
            </StatusCard>
        );
    }

    if (error) {
        return (
            <StatusCard title="Galeria de Treinamento">
                <div className="text-center py-8">
                    <p className="text-red-600 mb-4">❌ {error}</p>
                    <Button onClick={refresh} variant="primary" size="sm">
                        Tentar Novamente
                    </Button>
                </div>
            </StatusCard>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header com Estatísticas */}
            <StatusCard title="Galeria de Imagens de Treinamento">
                <div className="flex justify-between items-center mb-4">
                    <div className="flex items-center space-x-4">
                        <span className="text-sm font-medium">
                            {stats?.total_images || 0} imagens • {stats?.completion_percentage.toFixed(1) || 0}% completo
                        </span>
                        <div className={`px-2 py-1 rounded text-xs font-medium ${
                            stats?.training_complete ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'
                        }`}>
                            {stats?.training_complete ? 'Treinamento Completo' : 'Treinamento Pendente'}
                        </div>
                    </div>
                    
                    <Button onClick={refresh} variant="secondary" size="sm" icon={<RefreshCw />}>
                        Atualizar
                    </Button>
                </div>

                {/* Filtros por Categoria */}
                <div className="flex space-x-2 mb-6">
                    <button
                        onClick={() => setSelectedCategory('all')}
                        className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                            selectedCategory === 'all'
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                    >
                        Todas ({images.length})
                    </button>
                    
                    {/* Iteração sobre as categorias para criar os botões de filtro */}
                    {Object.entries(imagesByCategory).map(([category, categoryImages]) => (
                        <button
                            key={category}
                            onClick={() => setSelectedCategory(category)}
                            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                                selectedCategory === category
                                    ? 'bg-blue-500 text-white'
                                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                        >
                            {getCategoryDisplayName(category)} ({categoryImages.length})
                        </button>
                    ))}
                </div>

                {/* Grid de Imagens */}
                {filteredImages.length > 0 ? (
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                        {filteredImages.map((image) => (
                            <div
                                key={`${image.category}-${image.filename}`}
                                className="group relative bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow"
                            >
                                <img
                                    src={image.url} // <-- Esta é a URL que não está carregando a imagem
                                    alt={image.filename}
                                    className="w-full h-24 object-cover"
                                    onError={(e) => {
                                        // Substitui a imagem por um SVG de erro se não carregar
                                        (e.target as HTMLImageElement).src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIGZpbGw9Im5vbmUiIHN0cm9rZT0iY3VycmVudENvbG9yIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIgdmlld0JveD0iMCAwIDI0IDI0Ij48cGF0aCBkPSJtOSA5IDMgM0wyMCA0SDRsNSA1IDMtM3oiLz48cGF0aCBkPSJtMTUgMTMtMy0zVjI0aDEwdi0yMGwtNCA0eiIvPjwvc3ZnPg==';
                                    }}
                                />
                                
                                {/* Badge da Categoria (rendeizado corretamente com base em image.category) */}
                                <div className={`absolute top-1 left-1 px-2 py-1 rounded text-xs font-medium ${getCategoryColor(image.category)}`}>
                                    {getCategoryDisplayName(image.category)}
                                </div>
                                
                                {/* Overlay de Ações */}
                                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition-all duration-200 flex items-center justify-center">
                                    <div className="opacity-0 group-hover:opacity-100 transition-opacity space-x-1">
                                        <button
                                            onClick={() => setSelectedImage(image.url)}
                                            className="p-1 bg-white text-gray-700 rounded hover:bg-gray-100"
                                            title="Visualizar"
                                        >
                                            <Eye className="w-4 h-4" />
                                        </button>
                                        
                                        <a
                                            href={image.url}
                                            download={image.filename}
                                            className="inline-block p-1 bg-white text-gray-700 rounded hover:bg-gray-100"
                                            title="Download"
                                        >
                                            <Download className="w-4 h-4" />
                                        </a>
                                        
                                        <button
                                            onClick={() => handleDeleteImage(image.category, image.filename)}
                                            className="p-1 bg-red-500 text-white rounded hover:bg-red-600"
                                            title="Deletar"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                                
                                {/* Info da Imagem */}
                                <div className="p-2">
                                    <p className="text-xs font-mono text-gray-600 truncate">
                                        {image.filename}
                                    </p>
                                    <p className="text-xs text-gray-500">
                                        {image.created_at_formatted}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-12 text-gray-500">
                        <p>📷 Nenhuma imagem encontrada</p>
                        <p className="text-sm mt-1">
                            Use o sistema de treinamento para capturar imagens
                        </p>
                    </div>
                )}

                {/* Ações de Categoria */}
                {selectedCategory !== 'all' && filteredImages.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                        <Button
                            onClick={() => handleClearCategory(selectedCategory)}
                            variant="danger"
                            size="sm"
                            icon={<Trash2 />}
                        >
                            Limpar Categoria "{getCategoryDisplayName(selectedCategory)}"
                        </Button>
                    </div>
                )}
            </StatusCard>

            {/* Modal de Visualização (para quando clica no ícone de olho) */}
            {selectedImage && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50"
                    onClick={() => setSelectedImage(null)}
                >
                    <div className="max-w-4xl max-h-4xl p-4">
                        <img
                            src={selectedImage}
                            alt="Visualização"
                            className="max-w-full max-h-full object-contain rounded"
                            onClick={(e) => e.stopPropagation()}
                        />
                    </div>
                </div>
            )}
        </div>
    );
};