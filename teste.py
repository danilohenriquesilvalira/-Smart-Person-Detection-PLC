import cv2
import numpy as np
import time
import json
import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict

# =====================================
# 🎥 CONFIGURAÇÃO SISTEMA
# =====================================

RTSP_URL = "rtsp://DaniloLira:Danilo%4034333528@192.168.0.100:554/stream2"

# Estrutura de pastas
BASE_DIR = Path("eclusa_training_data")
FOTOS_TREINO_DIR = BASE_DIR / "copo_limpo"
CONFIG_FILE = BASE_DIR / "sistema_config.json"

# Parâmetros ajustados
MIN_FOTOS_TREINO = 8
THRESHOLD_BASE = 0.75 # Threshold inicial para similaridade de template

# =====================================
# 🧠 SISTEMA SIMPLIFICADO E PRECISO
# =====================================

class SistemaEclusaSimples:
    def __init__(self):
        self.modo = "SETUP"
        self.roi_coords = None
        self.threshold_deteccao = THRESHOLD_BASE
        self.fotos_treinamento = []
        self.sistema_treinado = False
        
        # Criar estrutura
        self.criar_estrutura_pastas()
        self.carregar_sistema()
        
        print("🧠 Sistema Simplificado inicializado")
    
    def criar_estrutura_pastas(self):
        """📁 Criar estrutura de pastas"""
        try:
            BASE_DIR.mkdir(exist_ok=True)
            FOTOS_TREINO_DIR.mkdir(exist_ok=True)
            print(f"📁 Estrutura criada: {BASE_DIR}")
        except Exception as e:
            print(f"❌ Erro criando pastas: {e}")
    
    def carregar_sistema(self):
        """📂 Carregar sistema salvo"""
        try:
            self.fotos_treinamento = []
            fotos_arquivos = sorted(FOTOS_TREINO_DIR.glob("*.jpg"))
            
            for foto_path in fotos_arquivos:
                foto = cv2.imread(str(foto_path), cv2.IMREAD_GRAYSCALE)
                if foto is not None:
                    foto_resized = cv2.resize(foto, (100, 100))
                    self.fotos_treinamento.append(foto_resized)
            
            print(f"📂 {len(self.fotos_treinamento)} templates carregados")
            
            # Carregar config
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.threshold_deteccao = config.get("threshold", THRESHOLD_BASE)
                    self.roi_coords = tuple(config["roi"]) if "roi" in config else None
            
            self.sistema_treinado = len(self.fotos_treinamento) >= MIN_FOTOS_TREINO
            
            if self.sistema_treinado:
                print(f"✅ Sistema treinado com {len(self.fotos_treinamento)} fotos")
            else:
                print(f"⚠️ Precisa de {MIN_FOTOS_TREINO - len(self.fotos_treinamento)} fotos para treinamento completo.")
                
        except Exception as e:
            print(f"❌ Erro carregando: {e}")
    
    def adicionar_foto_treinamento(self, roi: np.ndarray) -> Tuple[bool, str]:
        """📸 Adicionar foto de treinamento"""
        if roi is None or roi.size == 0:
            return False, "ROI inválida"
        
        try:
            # Converter para grayscale e redimensionar
            if len(roi.shape) == 3:
                roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:
                roi_gray = roi.copy()
            
            roi_resized = cv2.resize(roi_gray, (100, 100)) # Redimensionar para o template
            
            # Salvar arquivo original da ROI para revisão
            numero_foto = len(self.fotos_treinamento) + 1
            nome_arquivo = f"copo_limpo_{numero_foto:02d}.jpg"
            caminho_arquivo = FOTOS_TREINO_DIR / nome_arquivo
            
            cv2.imwrite(str(caminho_arquivo), roi) # Salvar a ROI original, não a redimensionada
            
            # Adicionar à lista de templates (redimensionada)
            self.fotos_treinamento.append(roi_resized)
            
            # Verificar se completou treinamento
            if len(self.fotos_treinamento) >= MIN_FOTOS_TREINO:
                self.sistema_treinado = True
                self.calcular_threshold_otimo() # Recalcular threshold após adicionar foto
            
            print(f"📸 Foto {numero_foto} salva!")
            print(f"📊 Progresso: {len(self.fotos_treinamento)}/{MIN_FOTOS_TREINO}")
            
            return True, f"Foto {numero_foto} adicionada"
            
        except Exception as e:
            return False, f"Erro ao adicionar foto: {e}"
    
    def calcular_threshold_otimo(self):
        """🎯 Calcular threshold ótimo"""
        if len(self.fotos_treinamento) < MIN_FOTOS_TREINO:
            print("⚠️ Não há fotos suficientes para calcular o threshold ótimo.")
            return
        
        try:
            similaridades = []
            
            # Comparar cada foto de treinamento com as outras
            for i in range(len(self.fotos_treinamento)):
                for j in range(i+1, len(self.fotos_treinamento)):
                    foto1 = self.fotos_treinamento[i]
                    foto2 = self.fotos_treinamento[j]
                    
                    # Garantir que as dimensões são as mesmas para template matching
                    if foto1.shape != foto2.shape:
                        foto2 = cv2.resize(foto2, foto1.shape[::-1])

                    result = cv2.matchTemplate(foto1, foto2, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    similaridades.append(max_val)
            
            if similaridades:
                # O threshold ótimo é um pouco abaixo da menor similaridade entre as fotos "limpas"
                min_similaridade = min(similaridades)
                self.threshold_deteccao = min_similaridade * 0.90 # Ajustado para 90% da menor similaridade
                
                print(f"🎯 Threshold otimizado: {self.threshold_deteccao:.3f}")
                self.salvar_configuracao()
                
        except Exception as e:
            print(f"❌ Erro calculando threshold ótimo: {e}")
            
    def detectar_objeto_horizontal(self, roi: np.ndarray) -> Tuple[bool, float, Dict]:
        """
        🎯 DETECTAR SE HÁ OBJETO ATRAVESSANDO HORIZONTALMENTE
        Aprimorado para ser mais robusto a cabos e objetos finos.
        """
        try:
            if len(roi.shape) == 3:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:
                gray = roi.copy()
            
            h, w = gray.shape
            
            # 1. DETECÇÃO DE BORDAS ADAPTATIVA
            # Usar Otsu's thresholding para encontrar um limiar de forma adaptativa
            # para binarizar a imagem antes de Canny, pode ajudar a realçar o cabo
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Aplicar Canny nas bordas
            # Parâmetros Canny mais baixos para capturar mais detalhes do cabo
            edges = cv2.Canny(thresh, 20, 80, apertureSize=3) 
            
            # 2. MORFOLOGIA para conectar segmentos de borda do cabo
            # Dilatação para conectar pequenos gaps nas bordas do cabo
            kernel_dilate = np.ones((3,3),np.uint8)
            edges_dilated = cv2.dilate(edges, kernel_dilate, iterations=1)
            
            # 3. ANÁLISE HORIZONTAL - BUSCAR LINHAS CONTÍNUAS (ou quase contínuas)
            linhas_horizontais_fortes = 0
            cobertura_horizontal_total = 0
            
            # Threshold de cobertura por linha (percentual de pixels de borda na linha)
            # Um valor menor (e.g., 0.3) significa que mesmo linhas parcialmente ocupadas contam
            MIN_COBERTURA_LINHA = 0.35 
            
            # Iterar por cada linha na imagem de bordas dilatadas
            for y in range(h):
                linha_pixels = edges_dilated[y, :]
                
                pixels_borda = np.sum(linha_pixels > 0)
                cobertura_linha = pixels_borda / w
                
                if cobertura_linha > MIN_COBERTURA_LINHA:
                    linhas_horizontais_fortes += 1
                    cobertura_horizontal_total += cobertura_linha
            
            # 4. CALCULAR SCORE DE OBJETO HORIZONTAL
            score_horizontal = 0.0
            percentual_linhas_ocupadas = linhas_horizontais_fortes / h if h > 0 else 0
            
            if linhas_horizontais_fortes > 0:
                cobertura_media_por_linha = cobertura_horizontal_total / linhas_horizontais_fortes
                
                # O score reflete o quão "horizontal" e "extenso" é o objeto
                # Ponderar mais a porcentagem de linhas ocupadas, pois indica um objeto mais espalhado verticalmente
                score_horizontal = (percentual_linhas_ocupadas * 0.6) + (cobertura_media_por_linha * 0.4)
            
            # DECISÃO: Um objeto horizontal é considerado presente se uma % razoável de linhas
            # tem detecção de borda e a cobertura média é decente.
            # Ajuste esses thresholds para a sensibilidade desejada ao cabo.
            tem_objeto_horizontal = (percentual_linhas_ocupadas > 0.10 and score_horizontal > 0.2) 
            # O percentual de linhas ocupadas pode ser menor para um cabo fino que se espalha verticalmente
            # Score horizontal pode ser menor para bordas mais esparsas de um cabo
            
            detalhes = {
                "linhas_com_objeto": linhas_horizontais_fortes,
                "total_linhas": h,
                "percentual_ocupado": percentual_linhas_ocupadas,
                "cobertura_media": cobertura_media_por_linha if linhas_horizontais_fortes > 0 else 0,
                "score_horizontal": score_horizontal,
                "pixels_borda_total": np.sum(edges > 0) # total de pixels de borda
            }
            
            return tem_objeto_horizontal, score_horizontal, detalhes
            
        except Exception as e:
            return False, 0.0, {"erro": str(e)}

    def detectar_cabo_enrolado(self, roi: np.ndarray) -> Tuple[bool, float, Dict]:
        """
        Detecta a presença de um cabo enrolado com base na análise de contornos
        que exibem características de curvas/círculos e alongamento.
        """
        try:
            if len(roi.shape) == 3:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:
                gray = roi.copy()

            h, w = gray.shape

            # Pré-processamento: Binarização e Canny para realçar bordas do cabo
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            edges = cv2.Canny(thresh, 50, 150, apertureSize=3) # Ajustar para pegar mais bordas do cabo

            # Operação morfológica para fechar pequenas lacunas nas bordas do cabo
            kernel = np.ones((3,3),np.uint8)
            edges_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1)
            
            contours, _ = cv2.findContours(edges_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            cabo_score_acumulado = 0.0
            num_contornos_cabo = 0
            
            for contour in contours:
                area = cv2.contourArea(contour)
                perimeter = cv2.arcLength(contour, True)

                # Filtrar contornos muito pequenos (ruído) ou muito grandes (fundo/objeto principal)
                # Os limites devem ser ajustados para o tamanho do seu cabo na ROI
                if area < 100 or area > (h * w * 0.7): # Ex: min 100 pixels, max 70% da ROI
                    continue
                
                # Calcular circularidade: 4 * pi * area / (perímetro * perímetro)
                circularity = (4 * np.pi * area) / (perimeter * perimeter) if perimeter > 0 else 0

                # Calcular "solidez": área do contorno / área do convex hull
                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                solidity = float(area)/hull_area if hull_area > 0 else 0

                # Calcular razão de aspecto (largura/altura do bounding box)
                x,y,w_c,h_c = cv2.boundingRect(contour)
                aspect_ratio = float(w_c)/h_c if h_c > 0 else 0

                # **Critérios para identificar contornos de cabo enrolado:**
                # 1. Circularidade: Cabos enrolados tendem a formar arcos ou círculos (0.1 a 0.8)
                # 2. Solidez: Cabos são relativamente "sólidos" (não muitos furos internos)
                # 3. Razão de Aspecto: Pode ser variada, mas para segmentos, pode não ser extrema
                # 4. Alongamento: Um cabo pode ter um contorno mais alongado (pode ser inferido do aspect_ratio)

                # Valores de threshold para circularidade e solidez precisam ser ajustados empiricamente
                # para o tipo de cabo e iluminação.
                is_cabo_segment = False
                if (0.15 < circularity < 0.85) and (solidity > 0.7): # Valores de exemplo
                    is_cabo_segment = True
                    # Pontuar baseado em quão bem ele se encaixa nos critérios
                    score_segmento = (circularity + solidity) / 2 
                    cabo_score_acumulado += score_segmento
                    num_contornos_cabo += 1
                elif (0.05 < aspect_ratio < 20) and solidity > 0.6 and area > 150: # Para segmentos mais alongados
                     is_cabo_segment = True
                     score_segmento = (solidity + (1/aspect_ratio if aspect_ratio>1 else aspect_ratio)) / 2 # Ponderar alongamento
                     cabo_score_acumulado += score_segmento
                     num_contornos_cabo += 1

            # Calcular score final: média do score dos segmentos de cabo detectados
            score_final_cabo_enrolado = cabo_score_acumulado / num_contornos_cabo if num_contornos_cabo > 0 else 0.0

            # Decisão final para "tem_cabo_enrolado"
            # Precisamos de um número mínimo de segmentos e um score médio razoável
            # Estes valores (2 contornos, 0.4 de score) são sugestões e precisam de ajuste
            tem_cabo_enrolado = (num_contornos_cabo >= 2 and score_final_cabo_enrolado > 0.4) 
            
            detalhes = {
                "num_contornos_total": len(contours),
                "num_contornos_cabo_like": num_contornos_cabo,
                "score_enrolado": score_final_cabo_enrolado,
                "pixels_borda_total": np.sum(edges > 0)
            }

            return tem_cabo_enrolado, score_final_cabo_enrolado, detalhes

        except Exception as e:
            return False, 0.0, {"erro": str(e)}

    def template_matching_simples(self, roi: np.ndarray) -> Tuple[float, Dict]:
        """🔍 Template matching simplificado"""
        if not self.fotos_treinamento:
            return 0.0, {"erro": "Nenhum template de treinamento carregado."}

        try:
            # Preprocessar ROI atual
            if len(roi.shape) == 3:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:
                gray = roi.copy()
            
            roi_resized = cv2.resize(gray, (100, 100))
            
            # Comparar com todas as fotos de treinamento
            similaridades = []
            
            for foto_treino in self.fotos_treinamento:
                # Certificar que as dimensões são compatíveis
                if foto_treino.shape != roi_resized.shape:
                    foto_treino = cv2.resize(foto_treino, roi_resized.shape[::-1])

                result = cv2.matchTemplate(roi_resized, foto_treino, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                similaridades.append(max_val)
            
            if similaridades:
                max_similaridade = max(similaridades)
                media_similaridade = np.mean(similaridades)
                
                # Conta quantas fotos deram match (acima do threshold)
                matches_ok = sum(1 for s in similaridades if s >= self.threshold_deteccao)
                percentual_match = (matches_ok / len(similaridades)) * 100 if len(similaridades) > 0 else 0
                
                detalhes = {
                    "max_similaridade": max_similaridade,
                    "media_similaridade": media_similaridade,
                    "percentual_match": percentual_match,
                    "threshold": self.threshold_deteccao
                }
                
                return max_similaridade, detalhes
            
            return 0.0, {"erro": "Nenhuma comparação de template realizada."}
            
        except Exception as e:
            return 0.0, {"erro": str(e)}
    
    def detectar_estado_final(self, roi: np.ndarray) -> Tuple[str, float, Dict]:
        """
        🎯 LÓGICA DE DECISÃO DE ESTADO FINAL APRIMORADA
        Prioriza detecção de cabo (horizontal ou enrolado), depois template matching.
        """
        if not self.sistema_treinado:
            return "NAO_TREINADO", 0.0, {"erro": "Sistema não treinado"}
        
        if roi is None or roi.size == 0:
            return "ERRO", 0.0, {"erro": "ROI inválida"}
        
        try:
            # 1. PRIMEIRA VERIFICAÇÃO: Objeto horizontal (cabo reto, barra, etc.)
            tem_horizontal, score_horizontal, detalhes_horizontal = self.detectar_objeto_horizontal(roi)
            
            # 2. SEGUNDA VERIFICAÇÃO: Cabo enrolado (contornos, circularidade)
            tem_cabo_enrolado, score_cabo_enrolado, detalhes_cabo_enrolado = self.detectar_cabo_enrolado(roi)

            # 3. TERCEIRA VERIFICAÇÃO: Template matching (similaridade com copo limpo)
            similaridade_template, detalhes_template = self.template_matching_simples(roi)
            
            # 4. DECISÃO FINAL: Ordem de prioridade
            
            estado = "INDEFINIDO" # Estado inicial
            confianca = 0.0
            motivo = ""

            # Prioridade 1: Cabo (seja horizontal ou enrolado)
            if tem_horizontal and score_horizontal > 0.25: # Ajuste o threshold de score horizontal se necessário
                estado = "OCUPADO"
                confianca = score_horizontal
                motivo = f"Cabo (ou objeto) horizontal detectado (score: {score_horizontal:.2f})"
            elif tem_cabo_enrolado and score_cabo_enrolado > 0.45: # Ajuste o threshold de score do cabo enrolado
                estado = "OCUPADO"
                confianca = score_cabo_enrolado
                motivo = f"Cabo enrolado detectado (score: {score_cabo_enrolado:.2f})"
            # Prioridade 2: Objeto Irregular (se não for LIVRE nem OCUPADO de forma clara)
            elif similaridade_template < (self.threshold_deteccao * 0.9): # Menor similaridade do que o "limpo"
                estado = "OBSTRUIDO"
                confianca = 1.0 - similaridade_template # Inverso da similaridade para indicar "diferença"
                motivo = f"Objeto irregular/não reconhecido (similaridade: {similaridade_template:.2f})"
            # Prioridade 3: LIVRE (se for similar ao copo limpo)
            elif similaridade_template >= self.threshold_deteccao:
                estado = "LIVRE"
                confianca = similaridade_template
                motivo = f"Similar ao copo limpo (similaridade: {similaridade_template:.2f})"
            else:
                # Caso onde não se encaixa claramente em nenhuma categoria principal
                # Pode ser um objeto com baixa similaridade mas que não ativou o "cabo" forte
                estado = "OBSTRUIDO" # Assumir obstruído por segurança em caso de dúvida
                confianca = max(0.0, 1.0 - similaridade_template)
                motivo = "Indefinido, assumindo obstruído por baixa similaridade ou detecção ambígua."
            
            # Combinar todos os detalhes para debug
            detalhes_completos = {
                "estado_final": estado,
                "motivo": motivo,
                "horizontal_analysis": detalhes_horizontal,
                "enrolado_analysis": detalhes_cabo_enrolado,
                "template_analysis": detalhes_template,
                "decisao_params": {
                    "tem_horizontal": tem_horizontal,
                    "score_horizontal": score_horizontal,
                    "tem_cabo_enrolado": tem_cabo_enrolado,
                    "score_cabo_enrolado": score_cabo_enrolado,
                    "similaridade_template": similaridade_template,
                    "threshold_template_usado": self.threshold_deteccao
                }
            }
            
            return estado, confianca, detalhes_completos
            
        except Exception as e:
            return "ERRO", 0.0, {"erro": str(e)}
    
    def salvar_configuracao(self):
        """💾 Salvar configuração"""
        try:
            config = {
                "threshold": self.threshold_deteccao,
                "roi": list(self.roi_coords) if self.roi_coords else None,
                "total_fotos": len(self.fotos_treinamento),
                "sistema_treinado": self.sistema_treinado,
                "timestamp": time.time()
            }
            
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
                
            print("💾 Configuração salva!")
        except Exception as e:
            print(f"❌ Erro salvando config: {e}")
    
    def limpar_treinamento(self):
        """🧹 Limpar treinamento"""
        try:
            for foto_file in FOTOS_TREINO_DIR.glob("*.jpg"):
                foto_file.unlink()
            
            if CONFIG_FILE.exists():
                CONFIG_FILE.unlink()
            
            self.fotos_treinamento = []
            self.sistema_treinado = False
            self.threshold_deteccao = THRESHOLD_BASE
            self.roi_coords = None # Resetar ROI também ao limpar treinamento
            
            print("🧹 Treinamento e configuração limpos!")
            
        except Exception as e:
            print(f"❌ Erro limpando: {e}")
    
    def get_status(self) -> Dict:
        """📊 Status do sistema"""
        return {
            "modo": self.modo,
            "sistema_treinado": self.sistema_treinado,
            "total_fotos": len(self.fotos_treinamento),
            "fotos_necessarias": max(0, MIN_FOTOS_TREINO - len(self.fotos_treinamento)),
            "threshold": self.threshold_deteccao,
            "roi_definida": self.roi_coords is not None
        }

# =====================================
# 🎮 INTERFACE PRINCIPAL SIMPLIFICADA
# =====================================

sistema = SistemaEclusaSimples()
roi_start = None
roi_end = None
drawing = False

def mouse_callback(event, x, y, flags, param):
    """🖱️ Callback do mouse para definir ROI"""
    global roi_start, roi_end, drawing, sistema
    
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        roi_start = (x, y)
        roi_end = (x, y)
        
    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            roi_end = (x, y)
            
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        roi_end = (x, y)
        
        x1 = min(roi_start[0], roi_end[0])
        y1 = min(roi_start[1], roi_end[1])
        x2 = max(roi_start[0], roi_end[0])
        y2 = max(roi_start[1], roi_end[1])
        
        # Validar tamanho mínimo da ROI para evitar ROIs muito pequenas
        if (x2 - x1) > 50 and (y2 - y1) > 50:
            sistema.roi_coords = (x1, y1, x2, y2)
            sistema.salvar_configuracao()
            print(f"🎯 ROI definida: {sistema.roi_coords}")
        else:
            print("⚠️ ROI muito pequena. Por favor, arraste para criar uma ROI maior.")

def conectar_camera():
    """📷 Conectar à câmera RTSP"""
    print("📷 Conectando à câmera...")
    
    cap = cv2.VideoCapture(RTSP_URL)
    # Tentar configurar o buffer para o menor possível para reduzir latência
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 
    
    if not cap.isOpened():
        print(f"❌ Erro: Não foi possível conectar à câmera no URL: {RTSP_URL}")
        print("Certifique-se de que o URL RTSP está correto e a câmera está acessível na rede.")
        return None
    
    # Tentar ler um frame para verificar se a conexão está ativa
    ret, frame = cap.read()
    if not ret:
        print("❌ Erro: Conectado à câmera, mas não foi possível ler um frame inicial.")
        cap.release()
        return None
    
    print("✅ Câmera conectada e frame lido!")
    return cap

def extrair_roi(frame, roi_coords):
    """✂️ Extrair ROI do frame"""
    if roi_coords is None:
        return None
    
    x1, y1, x2, y2 = roi_coords
    h, w = frame.shape[:2]
    
    # Garantir que as coordenadas da ROI estejam dentro dos limites do frame
    x1 = max(0, min(x1, w-1))
    y1 = max(0, min(y1, h-1))  
    x2 = max(x1, min(x2, w)) # x2 deve ser no mínimo x1
    y2 = max(y1, min(y2, h)) # y2 deve ser no mínimo y1

    if (x2 <= x1) or (y2 <= y1): # Se a ROI não tem dimensão válida (min 1x1 pixel)
        return None
        
    roi = frame[y1:y2, x1:x2]
    return roi if roi.size > 0 else None

def desenhar_interface(frame):
    """🎨 Interface visual simplificada"""
    frame_copy = frame.copy()
    h, w = frame_copy.shape[:2]
    
    # Desenhar ROI
    if sistema.roi_coords:
        x1, y1, x2, y2 = sistema.roi_coords
        
        cor_roi = (255, 255, 255) # Default branco
        if sistema.modo == "TREINAMENTO":
            cor_roi = (0, 255, 255)  # Amarelo para treinamento
        elif sistema.modo == "DETECCAO":
            # Cor da ROI muda com o estado detectado
            if sistema.roi_coords and sistema.sistema_treinado:
                roi_temp = extrair_roi(frame, sistema.roi_coords)
                if roi_temp is not None:
                    estado_atual, _, _ = sistema.detectar_estado_final(roi_temp)
                    if estado_atual == "LIVRE":
                        cor_roi = (0, 255, 0)       # Verde
                    elif estado_atual == "OCUPADO":
                        cor_roi = (0, 0, 255)       # Vermelho
                    elif estado_atual == "OBSTRUIDO":
                        cor_roi = (0, 165, 255)     # Laranja
                    else:
                        cor_roi = (128, 128, 128) # Cinza para indefinido/erro
                else:
                    cor_roi = (255, 0, 0) # Azul se ROI inválida
            else:
                cor_roi = (0, 255, 0)    # Verde padrão para detecção
        
        cv2.rectangle(frame_copy, (x1, y1), (x2, y2), cor_roi, 3)
        cv2.putText(frame_copy, f"ROI: {x2-x1}x{y2-y1}", 
                    (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor_roi, 2)
    
    # ROI temporária (arrastar)
    if drawing and roi_start and roi_end:
        cv2.rectangle(frame_copy, roi_start, roi_end, (255, 255, 0), 2) # Azul claro
    
    # Painel de status na parte inferior
    painel_h = 130 # Aumentado para mais informações
    painel = np.zeros((painel_h, w, 3), dtype=np.uint8)
    
    status = sistema.get_status()
    
    # Linha 1: Modo e Status Treinamento
    cor_modo = (0, 255, 255) if sistema.modo == "TREINAMENTO" else (0, 255, 0) if sistema.modo == "DETECCAO" else (255, 255, 255)
    cv2.putText(painel, f"MODO: {sistema.modo}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor_modo, 2)
    
    cor_treino_status = (0, 255, 0) if status["sistema_treinado"] else (0, 165, 255) # Laranja se não treinado
    cv2.putText(painel, f"FOTOS: {status['total_fotos']}/{MIN_FOTOS_TREINO}", 
                (250, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor_treino_status, 2)
    cv2.putText(painel, f"THRESHOLD (TPL): {status['threshold']:.2f}", 
                (450, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # Linha 2 & 3: Estado de Detecção (se em modo DETECCAO)
    if sistema.modo == "DETECCAO" and sistema.roi_coords and sistema.sistema_treinado:
        roi_process = extrair_roi(frame, sistema.roi_coords)
        if roi_process is not None:
            estado, confianca, detalhes = sistema.detectar_estado_final(roi_process)
            
            if estado == "LIVRE":
                cor_estado = (0, 255, 0)       # Verde
            elif estado == "OCUPADO":
                cor_estado = (0, 0, 255)       # Vermelho  
            elif estado == "OBSTRUIDO":
                cor_estado = (0, 165, 255)     # Laranja
            else:
                cor_estado = (255, 255, 255) # Branco para indefinido/erro
            
            cv2.putText(painel, f"ESTADO: {estado}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor_estado, 2)
            cv2.putText(painel, f"CONF: {confianca:.2f}", (280, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Informação adicional do motivo
            motivo_texto = detalhes.get("motivo", "N/A")
            cv2.putText(painel, motivo_texto[:70], (10, 85), # Limita o comprimento do texto
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

            # Scores de debug
            h_score = detalhes["decisao_params"]["score_horizontal"]
            e_score = detalhes["decisao_params"]["score_cabo_enrolado"]
            t_simil = detalhes["decisao_params"]["similaridade_template"]

            cv2.putText(painel, f"Score H: {h_score:.2f} | Score E: {e_score:.2f} | Simil T: {t_simil:.2f}", 
                        (10, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 255), 1)

        else:
            cv2.putText(painel, "ESTADO: ROI Invalida / Nao Definida", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    else:
        cv2.putText(painel, "Para deteccao: Defina ROI e Treine o sistema.", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)


    # Controles no frame principal
    cv2.putText(frame_copy, "ARRASTE: ROI | T: Treino | D: Deteccao | S: Salvar | C: Limpar | +/-: Threshold | G: Debug | ESC: Sair", 
                (10, h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    
    return np.vstack([frame_copy, painel]) # Empilha o frame da câmera e o painel de status

def mostrar_debug_detalhado(roi: np.ndarray):
    """🔍 Debug visual detalhado para análises de horizontalidade e contornos"""
    try:
        print("\n" + "="*60)
        print("🔍 DEBUG DETALHADO DA DETECÇÃO")
        print("="*60)
        
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi.copy()

        # Re-executar as análises para mostrar os resultados visuais
        tem_horizontal, score_horizontal, detalhes_h = sistema.detectar_objeto_horizontal(roi)
        tem_cabo_enrolado, score_enrolado, detalhes_e = sistema.detectar_cabo_enrolado(roi)
        similaridade, detalhes_t = sistema.template_matching_simples(roi)
        estado, confianca, detalhes_final = sistema.detectar_estado_final(roi)

        # Imagens para visualização
        roi_display = cv2.resize(roi, (320, 240))
        
        # Horizontal Analysis Image
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        edges_h = cv2.Canny(thresh, 20, 80, apertureSize=3)
        kernel_dilate = np.ones((3,3),np.uint8)
        edges_dilated_h = cv2.dilate(edges_h, kernel_dilate, iterations=1)
        edges_h_display = cv2.cvtColor(cv2.resize(edges_dilated_h, (320, 240)), cv2.COLOR_GRAY2BGR)
        
        # Enrolado Analysis Image
        edges_e = cv2.Canny(thresh, 50, 150, apertureSize=3)
        kernel_morph = np.ones((3,3),np.uint8)
        edges_closed_e = cv2.morphologyEx(edges_e, cv2.MORPH_CLOSE, kernel_morph, iterations=1)
        edges_e_display = cv2.cvtColor(cv2.resize(edges_closed_e, (320, 240)), cv2.COLOR_GRAY2BGR)
        
        # Desenhar contornos de cabo no debug visual
        if detalhes_e.get("num_contornos_cabo_like", 0) > 0:
            contours, _ = cv2.findContours(edges_closed_e, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Redimensionar contornos para a imagem de display
            scale_x = 320 / roi.shape[1]
            scale_y = 240 / roi.shape[0]
            
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                perimeter = cv2.arcLength(contour, True)
                if area >= 100: # Mostrar apenas contornos relevantes
                    # Calcular propriedades do contorno na imagem original para decisão
                    circularity = (4 * np.pi * area) / (perimeter * perimeter) if perimeter > 0 else 0
                    hull = cv2.convexHull(contour)
                    hull_area = cv2.contourArea(hull)
                    solidity = float(area)/hull_area if hull_area > 0 else 0
                    x,y,w_c,h_c = cv2.boundingRect(contour)
                    aspect_ratio = float(w_c)/h_c if h_c > 0 else 0

                    # Desenhar contornos que foram considerados "cabo-like" em vermelho, outros em azul
                    if ((0.15 < circularity < 0.85) and (solidity > 0.7)) or ((0.05 < aspect_ratio < 20) and solidity > 0.6 and area > 150):
                         color_contour = (0, 0, 255) # Vermelho
                    else:
                         color_contour = (255, 0, 0) # Azul

                    # Redimensionar e desenhar contorno na imagem de display
                    contour_scaled = (contour * np.array([scale_x, scale_y])).astype(np.int32)
                    cv2.drawContours(edges_e_display, [contour_scaled], -1, color_contour, 2)


        # Painel de Texto
        painel_info = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(painel_info, f"Estado: {estado}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(painel_info, f"Conf: {confianca:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(painel_info, f"Motivo: {detalhes_final.get('motivo', 'N/A')}", (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        cv2.putText(painel_info, "--- Horizontal ---", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(painel_info, f"Obj H: {tem_horizontal} (Score:{score_horizontal:.2f})", (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(painel_info, f"% Linhas: {detalhes_h.get('percentual_ocupado', 0):.1%}", (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        cv2.putText(painel_info, "--- Cabo Enrolado ---", (10, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(painel_info, f"Obj E: {tem_cabo_enrolado} (Score:{score_enrolado:.2f})", (10, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(painel_info, f"Contornos: {detalhes_e.get('num_contornos_cabo_like', 0)}/{detalhes_e.get('num_contornos_total', 0)}", (10, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Combinar todas as visualizações
        top_row = np.hstack([roi_display, edges_h_display])
        bottom_row = np.hstack([edges_e_display, painel_info])
        
        combined_debug = np.vstack([top_row, bottom_row])
        
        cv2.imshow("Debug Detalhado - Análises de Imagem", combined_debug)
        
        print(f"\n--- Análise Horizontal ---")
        print(f"  Tem Objeto Horizontal: {tem_horizontal}")
        print(f"  Score Horizontal: {score_horizontal:.3f}")
        print(f"  Detalhes: {detalhes_h}")

        print(f"\n--- Análise Cabo Enrolado ---")
        print(f"  Tem Cabo Enrolado: {tem_cabo_enrolado}")
        print(f"  Score Cabo Enrolado: {score_enrolado:.3f}")
        print(f"  Detalhes: {detalhes_e}")

        print(f"\n--- Análise Template Matching ---")
        print(f"  Similaridade com Template: {similaridade:.3f}")
        print(f"  Threshold para LIVRE: {sistema.threshold_deteccao:.3f}")
        print(f"  Detalhes: {detalhes_t}")

        print(f"\n--- Decisão Final ---")
        print(f"  Estado: {estado}")
        print(f"  Confiança: {confianca:.3f}")
        print(f"  Motivo: {detalhes_final.get('motivo', 'N/A')}")
        print("="*60)
        print("Pressione qualquer tecla na janela 'Debug Detalhado' para fechar...")
        cv2.waitKey(0)
        cv2.destroyWindow("Debug Detalhado - Análises de Imagem")
        
    except Exception as e:
        print(f"❌ Erro no debug detalhado: {e}")

def main():
    """🚀 Função principal"""
    print("="*60)
    print("🎯 SISTEMA ECLUSA SIMPLIFICADO AVANÇADO")
    print("="*60)
    print("🔧 LÓGICA DE DETECÇÃO APRIMORADA:")
    print("   • OCUPADO: Detecta cabos/objetos horizontais OU cabos enrolados.")  
    print("   • OBSTRUIDO: Objeto irregular/lixo (não é LIVRE nem OCUPADO de forma clara).")
    print("   • LIVRE: Similar ao 'copo limpo' (baseado em template matching).")
    print("="*60)
    
    cap = conectar_camera()
    if cap is None:
        return
    
    window_name = "Sistema Eclusa Simplificado"
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback)
    
    print("\n🎮 CONTROLES:")
    print("   🖱️   Arraste: Definir ou ajustar ROI")
    print("   T   Entrar no Modo Treinamento (para 'copo limpo')")
    print("   D   Entrar no Modo Detecção")  
    print("   S   Salvar foto para treinamento (no modo Treinamento)")
    print("   C   Limpar todo o treinamento e configuração")
    print("   G   Mostrar Janela de Debug Detalhado (no modo Detecção)")
    print("   +/- Ajustar Threshold do Template Matching")
    print("   ESC Sair do programa")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Não foi possível ler o frame da câmera. Tentando novamente...")
                time.sleep(0.5)
                continue
            
            # Interface principal
            frame_display = desenhar_interface(frame)
            cv2.imshow(window_name, frame_display)
            
            # ROI separada
            if sistema.roi_coords:
                roi = extrair_roi(frame, sistema.roi_coords)
                if roi is not None:
                    roi_display = cv2.resize(roi, (300, 200)) # Tamanho fixo para display
                    
                    if sistema.modo == "DETECCAO" and sistema.sistema_treinado:
                        estado, confianca, _ = sistema.detectar_estado_final(roi)
                        
                        # Cores para o texto do estado na janela da ROI
                        cor_texto = (0, 255, 0) if estado == "LIVRE" else (0, 0, 255) if estado == "OCUPADO" else (0, 165, 255)
                        
                        cv2.putText(roi_display, estado, (10, 30), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor_texto, 2)
                        cv2.putText(roi_display, f"Conf: {confianca:.2f}", (10, 60), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    cv2.imshow("ROI Visualizacao", roi_display) # Nome diferente para não sobrepor
                else:
                    # Se a ROI for inválida (ex: 0x0), fechar a janela de ROI
                    try:
                        cv2.destroyWindow("ROI Visualizacao")
                    except cv2.error:
                        pass # Janela já pode estar fechada
            else:
                # Se não há ROI definida, garantir que a janela da ROI não está aberta
                try:
                    cv2.destroyWindow("ROI Visualizacao")
                except cv2.error:
                    pass

            # Teclas
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27:  # ESC
                break
            elif key == ord('t') or key == ord('T'):
                sistema.modo = "TREINAMENTO"
                print("📚 Modo TREINAMENTO ativado.")
            elif key == ord('d') or key == ord('D'):
                if sistema.sistema_treinado:
                    sistema.modo = "DETECCAO"
                    print("🎯 Modo DETECÇÃO ativado.")
                else:
                    status = sistema.get_status()
                    print(f"⚠️ Sistema não treinado. Faltam {status['fotos_necessarias']} fotos para o treinamento.")
            elif key == ord('s') or key == ord('S'):
                if sistema.modo == "TREINAMENTO" and sistema.roi_coords:
                    roi_to_save = extrair_roi(frame, sistema.roi_coords)
                    if roi_to_save is not None:
                        sucesso, mensagem = sistema.adicionar_foto_treinamento(roi_to_save)
                        print(f"{'✅' if sucesso else '❌'} {mensagem}")
                    else:
                        print("⚠️ Não foi possível salvar: ROI inválida ou não definida.")
                else:
                    print("⚠️ Para salvar foto, entre no modo TREINAMENTO e defina a ROI primeiro.")
            elif key == ord('c') or key == ord('C'):
                sistema.limpar_treinamento()
            elif key == ord('+') or key == ord('='):
                sistema.threshold_deteccao = min(0.95, sistema.threshold_deteccao + 0.01) # Incremento menor
                sistema.salvar_configuracao()
                print(f"⬆️ Threshold de template matching aumentado para: {sistema.threshold_deteccao:.2f}")
            elif key == ord('-'):
                sistema.threshold_deteccao = max(0.1, sistema.threshold_deteccao - 0.01) # Decremento menor
                sistema.salvar_configuracao()
                print(f"⬇️ Threshold de template matching diminuído para: {sistema.threshold_deteccao:.2f}")
            elif key == ord('g') or key == ord('G'):
                if sistema.modo == "DETECCAO" and sistema.roi_coords and sistema.sistema_treinado:
                    roi_for_debug = extrair_roi(frame, sistema.roi_coords)
                    if roi_for_debug is not None:
                        mostrar_debug_detalhado(roi_for_debug)
                    else:
                        print("⚠️ Não foi possível iniciar debug: ROI inválida ou não definida.")
                else:
                    print("⚠️ Para usar o debug detalhado, entre no modo DETECÇÃO e treine o sistema primeiro.")
    
    except KeyboardInterrupt:
        print("\n🛑 Interrompido pelo usuário.")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("🧹 Sistema finalizado.")

if __name__ == "__main__":
    main()