// 🌐 src/hooks/useTrainingImages.ts - Hook para Imagens de Treinamento

import { useState, useEffect } from 'react';

interface TrainingImage {
  filename: string;
  category: string;
  url: string;
  created_at: number;
  created_at_formatted: string;
  size: number;
}

interface TrainingStats {
  total_images: number;
  images_by_category: Record<string, number>;
  training_complete: boolean;
  completion_percentage: number;
  categories: string[];
  detailed_progress: Record<string, any>;
}

export const useTrainingImages = () => {
  const [images, setImages] = useState<TrainingImage[]>([]);
  const [stats, setStats] = useState<TrainingStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchImages = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('http://localhost:5000/api/training/images');
      const data = await response.json();

      if (data.success) {
        setImages(data.data.images);
      } else {
        setError(data.error || 'Erro ao carregar imagens');
      }
    } catch (err) {
      setError('Erro de conexão com a API');
      console.error('Erro:', err);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/training/stats');
      const data = await response.json();

      if (data.success) {
        setStats(data.data);
      }
    } catch (err) {
      console.error('Erro ao carregar estatísticas:', err);
    }
  };

  const deleteImage = async (category: string, filename: string) => {
    try {
      const response = await fetch(
        `http://localhost:5000/api/training/image/${category}/${filename}`, 
        { method: 'DELETE' }
      );
      
      const data = await response.json();
      
      if (data.success) {
        // Recarregar imagens
        await fetchImages();
        await fetchStats();
        return true;
      } else {
        setError(data.error || 'Erro ao deletar imagem');
        return false;
      }
    } catch (err) {
      setError('Erro ao deletar imagem');
      console.error('Erro:', err);
      return false;
    }
  };

  const clearCategory = async (category: string) => {
    try {
      const response = await fetch(
        `http://localhost:5000/api/training/category/${category}/clear`,
        { method: 'POST' }
      );
      
      const data = await response.json();
      
      if (data.success) {
        await fetchImages();
        await fetchStats();
        return data.data.deleted_count;
      } else {
        setError(data.error || 'Erro ao limpar categoria');
        return 0;
      }
    } catch (err) {
      setError('Erro ao limpar categoria');
      console.error('Erro:', err);
      return 0;
    }
  };

  useEffect(() => {
    const loadData = async () => {
      await Promise.all([fetchImages(), fetchStats()]);
      setLoading(false);
    };

    loadData();
  }, []);

  return {
    images,
    stats,
    loading,
    error,
    refresh: async () => {
      await fetchImages();
      await fetchStats();
    },
    deleteImage,
    clearCategory
  };
};