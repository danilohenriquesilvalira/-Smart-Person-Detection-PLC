"""
🛠️ Utilitários de Imagem - Smart Detection Backend
"""
import os
import cv2
import base64
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json

from ..models.detection_model import TrainingImage, TrainingStats
from config.settings import TRAINING_CONFIG, get_training_paths

class ImageManager:
    """🖼️ Gerenciador de imagens de treinamento"""
    
    def __init__(self):
        self.training_paths = get_training_paths()
        self.allowed_extensions = TRAINING_CONFIG["image_extensions"]
        self.max_photos_per_class = TRAINING_CONFIG["max_photos_per_class"]
    
    def get_all_training_images(self) -> List[TrainingImage]:
        """📋 Listar todas as imagens de treinamento"""
        all_images = []
        
        for category, path in self.training_paths.items():
            if path.exists():
                for image_file in path.glob("*"):
                    if image_file.suffix.lower() in self.allowed_extensions:
                        try:
                            stat = image_file.stat()
                            image = TrainingImage(
                                filename=image_file.name,
                                category=category,
                                path=str(image_file),
                                created_at=stat.st_mtime,
                                size=stat.st_size
                            )
                            all_images.append(image)
                        except Exception as e:
                            print(f"❌ Erro ao processar {image_file}: {e}")
        
        # Ordenar por data de criação
        all_images.sort(key=lambda x: x.created_at, reverse=True)
        return all_images
    
    def get_images_by_category(self, category: str) -> List[TrainingImage]:
        """📁 Listar imagens por categoria"""
        if category not in self.training_paths:
            return []
        
        images = []
        path = self.training_paths[category]
        
        if path.exists():
            for image_file in sorted(path.glob("*")):
                if image_file.suffix.lower() in self.allowed_extensions:
                    try:
                        stat = image_file.stat()
                        image = TrainingImage(
                            filename=image_file.name,
                            category=category,
                            path=str(image_file),
                            created_at=stat.st_mtime,
                            size=stat.st_size
                        )
                        images.append(image)
                    except Exception as e:
                        print(f"❌ Erro ao processar {image_file}: {e}")
        
        return images
    
    def get_image_path(self, category: str, filename: str) -> Optional[Path]:
        """🔍 Obter caminho da imagem"""
        if category not in self.training_paths:
            return None
        
        image_path = self.training_paths[category] / filename
        
        if image_path.exists() and image_path.suffix.lower() in self.allowed_extensions:
            return image_path
        
        return None
    
    def get_training_stats(self) -> TrainingStats:
        """📊 Obter estatísticas de treinamento"""
        images_by_category = {}
        total_images = 0
        
        for category in self.training_paths.keys():
            count = len(self.get_images_by_category(category))
            images_by_category[category] = count
            total_images += count
        
        # Calcular porcentagem de completude
        max_total = len(self.training_paths) * self.max_photos_per_class
        completion_percentage = (total_images / max_total) * 100 if max_total > 0 else 0
        
        # Verificar se treinamento está completo
        training_complete = all(
            count >= self.max_photos_per_class 
            for count in images_by_category.values()
        )
        
        return TrainingStats(
            total_images=total_images,
            images_by_category=images_by_category,
            training_complete=training_complete,
            completion_percentage=min(completion_percentage, 100),
            categories=list(self.training_paths.keys())
        )
    
    def image_to_base64(self, image_path: Path) -> Optional[str]:
        """🔄 Converter imagem para base64"""
        try:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                base64_string = base64.b64encode(image_data).decode('utf-8')
                return f"data:image/jpeg;base64,{base64_string}"
        except Exception as e:
            print(f"❌ Erro ao converter imagem para base64: {e}")
            return None
    
    def save_training_image(self, image_array: np.ndarray, category: str) -> Optional[str]:
        """💾 Salvar imagem de treinamento"""
        if category not in self.training_paths:
            return None
        
        # Contar imagens existentes
        existing_count = len(self.get_images_by_category(category))
        
        if existing_count >= self.max_photos_per_class:
            print(f"⚠️ Máximo de imagens atingido para {category}")
            return None
        
        # Gerar nome do arquivo
        next_number = existing_count + 1
        filename = f"{category}_{next_number:02d}.jpg"
        image_path = self.training_paths[category] / filename
        
        try:
            # Salvar imagem
            success = cv2.imwrite(str(image_path), image_array)
            
            if success:
                print(f"💾 Imagem salva: {filename}")
                return filename
            else:
                print(f"❌ Falha ao salvar imagem: {filename}")
                return None
                
        except Exception as e:
            print(f"❌ Erro ao salvar imagem: {e}")
            return None
    
    def delete_image(self, category: str, filename: str) -> bool:
        """🗑️ Deletar imagem de treinamento"""
        image_path = self.get_image_path(category, filename)
        
        if not image_path:
            return False
        
        try:
            image_path.unlink()
            print(f"🗑️ Imagem deletada: {filename}")
            return True
        except Exception as e:
            print(f"❌ Erro ao deletar imagem: {e}")
            return False
    
    def clear_category(self, category: str) -> int:
        """🧹 Limpar todas as imagens de uma categoria"""
        if category not in self.training_paths:
            return 0
        
        deleted_count = 0
        images = self.get_images_by_category(category)
        
        for image in images:
            if self.delete_image(category, image.filename):
                deleted_count += 1
        
        return deleted_count
    
    def clear_all_training_data(self) -> int:
        """🧹 Limpar todos os dados de treinamento"""
        total_deleted = 0
        
        for category in self.training_paths.keys():
            deleted = self.clear_category(category)
            total_deleted += deleted
            print(f"🧹 {category}: {deleted} imagens removidas")
        
        print(f"🧹 Total: {total_deleted} imagens removidas")
        return total_deleted
    
    def get_category_progress(self, category: str) -> Dict:
        """📊 Progresso de uma categoria"""
        current_count = len(self.get_images_by_category(category))
        percentage = (current_count / self.max_photos_per_class) * 100
        
        return {
            "category": category,
            "current": current_count,
            "target": self.max_photos_per_class,
            "percentage": min(percentage, 100),
            "complete": current_count >= self.max_photos_per_class
        }

def resize_image_for_training(image: np.ndarray, target_size: Tuple[int, int] = (100, 100)) -> np.ndarray:
    """🔄 Redimensionar imagem para treinamento"""
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    return cv2.resize(image, target_size)

def extract_roi_from_frame(frame: np.ndarray, roi_coords: Tuple[int, int, int, int]) -> np.ndarray:
    """✂️ Extrair região de interesse do frame"""
    x1, y1, x2, y2 = roi_coords
    roi = frame[y1:y2, x1:x2]
    return resize_image_for_training(roi)

def validate_image_file(file_path: Path) -> bool:
    """✅ Validar se arquivo é uma imagem válida"""
    if not file_path.exists():
        return False
    
    if file_path.suffix.lower() not in TRAINING_CONFIG["image_extensions"]:
        return False
    
    try:
        # Tentar carregar a imagem
        image = cv2.imread(str(file_path))
        return image is not None
    except:
        return False

# 🏭 Instância global do gerenciador
image_manager = ImageManager()