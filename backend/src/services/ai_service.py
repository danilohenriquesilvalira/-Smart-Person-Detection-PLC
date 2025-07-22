"""
🔧 Serviço de IA - Smart Detection Backend
"""
import cv2
import numpy as np
import time
from typing import List, Dict, Optional, Tuple
from collections import Counter

from ..models.detection_model import DetectionValues, DetectionState, TrainingCounters
from config.settings import DETECTION_CONFIG, TRAINING_CONFIG

class AIService:
    """🤖 Serviço de Inteligência Artificial para Detecção"""
    
    def __init__(self):
        # Configurações
        self.sensitivity = DETECTION_CONFIG["default_sensitivity"]
        self.stability_history_size = DETECTION_CONFIG["stability_history_size"]
        self.stability_threshold = DETECTION_CONFIG["stability_threshold"]
        
        # Dados de treinamento
        self.training_images = {
            "sem_copo": [],
            "copo_bom": [],
            "copo_danificado": []
        }
        
        # Estado da IA
        self.is_trained = False
        self.training_counters = TrainingCounters()
        
        # Histórico de detecções para estabilidade
        self.detection_history = []
        self.last_stable_detection = DetectionState.SEM_COPO
        
        # Estatísticas
        self.detection_stats = {
            "total_detections": 0,
            "correct_detections": 0,
            "false_positives": 0,
            "last_detection_time": None,
            "average_processing_time": 0.0
        }
        
        print("🤖 Serviço de IA inicializado")
    
    def load_training_images(self, training_data: Dict[str, List[np.ndarray]]) -> bool:
        """📚 Carregar imagens de treinamento"""
        try:
            total_loaded = 0
            
            for category, images in training_data.items():
                if category in self.training_images:
                    self.training_images[category] = images.copy()
                    total_loaded += len(images)
                    print(f"📚 {category}: {len(images)} imagens carregadas")
            
            # Atualizar contadores
            self.training_counters = TrainingCounters(
                sem_copo=len(self.training_images["sem_copo"]),
                copo_bom=len(self.training_images["copo_bom"]),
                copo_danificado=len(self.training_images["copo_danificado"])
            )
            
            # Verificar se está treinado
            self.is_trained = self.training_counters.is_complete()
            
            print(f"🤖 IA carregada: {total_loaded} imagens, Treinado: {self.is_trained}")
            return True
            
        except Exception as e:
            print(f"❌ Erro carregando imagens de treinamento: {e}")
            return False
    
    def add_training_image(self, category: str, image: np.ndarray) -> bool:
        """➕ Adicionar imagem de treinamento"""
        if category not in self.training_images:
            print(f"❌ Categoria inválida: {category}")
            return False
        
        max_images = TRAINING_CONFIG["max_photos_per_class"]
        
        if len(self.training_images[category]) >= max_images:
            print(f"⚠️ Máximo de imagens atingido para {category}")
            return False
        
        try:
            # Preprocessar imagem
            processed_image = self._preprocess_training_image(image)
            
            # Adicionar à coleção
            self.training_images[category].append(processed_image)
            
            # Atualizar contador
            if category == "sem_copo":
                self.training_counters.sem_copo += 1
            elif category == "copo_bom":
                self.training_counters.copo_bom += 1
            elif category == "copo_danificado":
                self.training_counters.copo_danificado += 1
            
            # Verificar se está completo
            self.is_trained = self.training_counters.is_complete()
            
            print(f"➕ Imagem adicionada: {category} ({len(self.training_images[category])}/{max_images})")
            
            if self.is_trained and not self._was_previously_trained():
                print("🎉 Treinamento completo! IA pronta para detecção.")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro adicionando imagem de treinamento: {e}")
            return False
    
    def _preprocess_training_image(self, image: np.ndarray) -> np.ndarray:
        """🔧 Preprocessar imagem para treinamento"""
        # Converter para grayscale se necessário
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Redimensionar para tamanho padrão
        target_size = TRAINING_CONFIG.get("image_size", (100, 100))
        image = cv2.resize(image, target_size)
        
        # Normalização opcional (pode ser adicionada no futuro)
        # image = cv2.equalizeHist(image)
        
        return image
    
    def _was_previously_trained(self) -> bool:
        """🔍 Verificar se já estava treinado antes"""
        return (self.training_counters.sem_copo > 1 or 
                self.training_counters.copo_bom > 1 or 
                self.training_counters.copo_danificado > 1)
    
    def detect(self, input_image: np.ndarray) -> Tuple[DetectionValues, DetectionState]:
        """🎯 Realizar detecção na imagem"""
        start_time = time.time()
        
        if not self.is_trained:
            print("⚠️ IA não está treinada")
            return DetectionValues(), DetectionState.SEM_COPO
        
        try:
            # Preprocessar imagem de entrada
            processed_image = self._preprocess_detection_image(input_image)
            
            # Calcular valores de similaridade
            detection_values = self._calculate_similarities(processed_image)
            
            # Determinar estado detectado
            raw_detection = self._determine_detection_state(detection_values)
            
            # Aplicar filtro de estabilidade
            stable_detection = self._apply_stability_filter(raw_detection)
            
            # Atualizar estatísticas
            processing_time = time.time() - start_time
            self._update_detection_stats(stable_detection, processing_time)
            
            return detection_values, stable_detection
            
        except Exception as e:
            print(f"❌ Erro na detecção: {e}")
            processing_time = time.time() - start_time
            self._update_detection_stats(None, processing_time)
            return DetectionValues(), DetectionState.SEM_COPO
    
    def _preprocess_detection_image(self, image: np.ndarray) -> np.ndarray:
        """🔧 Preprocessar imagem para detecção"""
        # Mesmo preprocessamento do treinamento
        return self._preprocess_training_image(image)
    
    def _calculate_similarities(self, image: np.ndarray) -> DetectionValues:
        """🧮 Calcular similaridades com imagens de treinamento"""
        detection_values = DetectionValues()
        
        # Sem copo
        if self.training_images["sem_copo"]:
            detection_values.sem_copo = self._calculate_category_similarity(
                image, self.training_images["sem_copo"]
            )
        
        # Copo bom
        if self.training_images["copo_bom"]:
            detection_values.copo_bom = self._calculate_category_similarity(
                image, self.training_images["copo_bom"]
            )
        
        # Copo danificado
        if self.training_images["copo_danificado"]:
            detection_values.copo_danificado = self._calculate_category_similarity(
                image, self.training_images["copo_danificado"]
            )
        
        return detection_values
    
    def _calculate_category_similarity(self, image: np.ndarray, 
                                     training_images: List[np.ndarray]) -> float:
        """📊 Calcular similaridade com uma categoria"""
        if not training_images:
            return 0.0
        
        similarities = []
        
        for training_image in training_images:
            try:
                # Template matching normalizado
                result = cv2.matchTemplate(image, training_image, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                similarities.append(max_val)
            except Exception as e:
                print(f"⚠️ Erro calculando similaridade: {e}")
                continue
        
        if not similarities:
            return 0.0
        
        # Estratégias de agregação
        similarities.sort(reverse=True)
        
        # Média das 3 melhores (ou todas se menos que 3)
        top_n = min(3, len(similarities))
        top_similarities = similarities[:top_n]
        
        return float(np.mean(top_similarities))
    
    def _determine_detection_state(self, values: DetectionValues) -> DetectionState:
        """🎯 Determinar estado baseado nos valores"""
        # Ordenar valores por magnitude
        detections = [
            (DetectionState.SEM_COPO, values.sem_copo),
            (DetectionState.COPO_BOM, values.copo_bom),
            (DetectionState.COPO_DANIFICADO, values.copo_danificado)
        ]
        
        detections.sort(key=lambda x: x[1], reverse=True)
        
        # Estado com maior valor
        best_state, best_value = detections[0]
        second_state, second_value = detections[1]
        
        # Aplicar sensibilidade
        confidence = best_value - second_value
        
        if confidence >= self.sensitivity:
            return best_state
        else:
            # Incerteza - manter estado anterior
            return self.last_stable_detection
    
    def _apply_stability_filter(self, detection: DetectionState) -> DetectionState:
        """🔒 Aplicar filtro de estabilidade"""
        # Adicionar ao histórico
        self.detection_history.append(detection)
        
        # Limitar tamanho do histórico
        if len(self.detection_history) > self.stability_history_size:
            self.detection_history.pop(0)
        
        # Verificar estabilidade
        if len(self.detection_history) >= self.stability_threshold:
            # Contar ocorrências
            counter = Counter(self.detection_history)
            most_common_state, occurrences = counter.most_common(1)[0]
            
            # Se estado mais comum aparece pelo menos stability_threshold vezes
            if occurrences >= self.stability_threshold:
                if most_common_state != self.last_stable_detection:
                    print(f"🎯 Nova detecção estável: {most_common_state.value}")
                    self.last_stable_detection = most_common_state
                
                return most_common_state
        
        return self.last_stable_detection
    
    def _update_detection_stats(self, detection: Optional[DetectionState], processing_time: float):
        """📊 Atualizar estatísticas de detecção"""
        self.detection_stats["total_detections"] += 1
        self.detection_stats["last_detection_time"] = time.time()
        
        # Média móvel do tempo de processamento
        current_avg = self.detection_stats["average_processing_time"]
        total = self.detection_stats["total_detections"]
        
        self.detection_stats["average_processing_time"] = (
            (current_avg * (total - 1) + processing_time) / total
        )
    
    def set_sensitivity(self, sensitivity: float) -> bool:
        """⚙️ Configurar sensibilidade"""
        min_sens = DETECTION_CONFIG["min_sensitivity"]
        max_sens = DETECTION_CONFIG["max_sensitivity"]
        
        if not (min_sens <= sensitivity <= max_sens):
            print(f"❌ Sensibilidade fora dos limites: {min_sens} <= {sensitivity} <= {max_sens}")
            return False
        
        self.sensitivity = sensitivity
        print(f"⚙️ Sensibilidade atualizada: {sensitivity}")
        return True
    
    def reset_training(self) -> None:
        """🔄 Reset completo do treinamento"""
        print("🔄 Resetando treinamento da IA...")
        
        # Limpar imagens
        for category in self.training_images:
            self.training_images[category] = []
        
        # Reset contadores
        self.training_counters = TrainingCounters()
        
        # Reset estado
        self.is_trained = False
        self.detection_history = []
        self.last_stable_detection = DetectionState.SEM_COPO
        
        # Reset estatísticas
        self.detection_stats = {
            "total_detections": 0,
            "correct_detections": 0,
            "false_positives": 0,
            "last_detection_time": None,
            "average_processing_time": 0.0
        }
        
        print("✅ IA resetada")
    
    def get_training_progress(self) -> Dict:
        """📊 Obter progresso do treinamento"""
        max_per_class = TRAINING_CONFIG["max_photos_per_class"]
        
        return {
            "sem_copo": {
                "current": self.training_counters.sem_copo,
                "target": max_per_class,
                "percentage": (self.training_counters.sem_copo / max_per_class) * 100
            },
            "copo_bom": {
                "current": self.training_counters.copo_bom,
                "target": max_per_class,
                "percentage": (self.training_counters.copo_bom / max_per_class) * 100
            },
            "copo_danificado": {
                "current": self.training_counters.copo_danificado,
                "target": max_per_class,
                "percentage": (self.training_counters.copo_danificado / max_per_class) * 100
            },
            "total": {
                "current": self.training_counters.get_total(),
                "target": max_per_class * 3,
                "percentage": (self.training_counters.get_total() / (max_per_class * 3)) * 100
            },
            "is_complete": self.is_trained
        }
    
    def get_status(self) -> Dict:
        """📊 Obter status completo da IA"""
        return {
            "trained": self.is_trained,
            "sensitivity": self.sensitivity,
            "training_counters": self.training_counters.to_dict(),
            "last_stable_detection": self.last_stable_detection.value,
            "detection_history_size": len(self.detection_history),
            "statistics": self.detection_stats.copy(),
            "training_progress": self.get_training_progress(),
            "memory_usage": {
                "sem_copo_images": len(self.training_images["sem_copo"]),
                "copo_bom_images": len(self.training_images["copo_bom"]),
                "copo_danificado_images": len(self.training_images["copo_danificado"])
            }
        }
    
    def validate_training_completeness(self) -> Tuple[bool, List[str]]:
        """✅ Validar completude do treinamento"""
        issues = []
        max_per_class = TRAINING_CONFIG["max_photos_per_class"]
        
        for category in ["sem_copo", "copo_bom", "copo_danificado"]:
            count = len(self.training_images[category])
            if count < max_per_class:
                issues.append(f"{category}: {count}/{max_per_class} imagens")
        
        is_complete = len(issues) == 0
        
        return is_complete, issues
    
    def __del__(self):
        """🧹 Limpeza na destruição"""
        print("🧹 Serviço de IA finalizado")

# 🏭 Instância global do serviço de IA
ai_service = AIService()