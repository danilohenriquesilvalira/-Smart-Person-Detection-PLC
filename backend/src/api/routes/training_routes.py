"""
🌐 Rotas de Treinamento - Smart Detection API
"""
from flask import Blueprint, jsonify, request, send_file
from pathlib import Path
import mimetypes
import os

from ...utils.image_utils import image_manager
from ...models.detection_model import TrainingStats
from config.settings import TRAINING_CONFIG

# 🛣️ Blueprint para rotas de treinamento
training_bp = Blueprint('training', __name__, url_prefix='/api/training')

@training_bp.route('/images', methods=['GET'])
def get_all_training_images():
    """📋 Listar todas as imagens de treinamento"""
    try:
        images = image_manager.get_all_training_images()
        
        # Converter para formato JSON
        images_data = []
        for img in images:
            img_data = img.to_dict()
            # Adicionar URL para visualização
            img_data['url'] = f'/api/training/image/{img.category}/{img.filename}'
            # Formatar timestamp
            img_data['created_at_formatted'] = format_timestamp(img.created_at)
            images_data.append(img_data)
        
        return jsonify({
            "success": True,
            "data": {
                "images": images_data,
                "total": len(images_data)
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@training_bp.route('/images/<category>', methods=['GET'])
def get_images_by_category(category):
    """📁 Listar imagens por categoria"""
    try:
        # Validar categoria
        valid_categories = TRAINING_CONFIG["classes"]
        if category not in valid_categories:
            return jsonify({
                "success": False,
                "error": f"Categoria inválida. Categorias válidas: {valid_categories}"
            }), 400
        
        images = image_manager.get_images_by_category(category)
        
        # Converter para formato JSON
        images_data = []
        for img in images:
            img_data = img.to_dict()
            img_data['url'] = f'/api/training/image/{img.category}/{img.filename}'
            img_data['created_at_formatted'] = format_timestamp(img.created_at)
            images_data.append(img_data)
        
        # Obter progresso da categoria
        progress = image_manager.get_category_progress(category)
        
        return jsonify({
            "success": True,
            "data": {
                "category": category,
                "images": images_data,
                "count": len(images_data),
                "progress": progress
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@training_bp.route('/image/<category>/<filename>', methods=['GET'])
def get_training_image(category, filename):
    """🖼️ Obter imagem individual"""
    try:
        image_path = image_manager.get_image_path(category, filename)
        
        if not image_path:
            return jsonify({
                "success": False,
                "error": "Imagem não encontrada"
            }), 404
        
        # Determinar tipo MIME
        mime_type, _ = mimetypes.guess_type(str(image_path))
        if not mime_type:
            mime_type = 'image/jpeg'
        
        return send_file(
            str(image_path),
            mimetype=mime_type,
            as_attachment=False,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@training_bp.route('/image/<category>/<filename>/base64', methods=['GET'])
def get_training_image_base64(category, filename):
    """🔄 Obter imagem como base64"""
    try:
        image_path = image_manager.get_image_path(category, filename)
        
        if not image_path:
            return jsonify({
                "success": False,
                "error": "Imagem não encontrada"
            }), 404
        
        base64_data = image_manager.image_to_base64(image_path)
        
        if not base64_data:
            return jsonify({
                "success": False,
                "error": "Erro ao converter imagem para base64"
            }), 500
        
        return jsonify({
            "success": True,
            "data": {
                "filename": filename,
                "category": category,
                "base64": base64_data,
                "size": image_path.stat().st_size
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@training_bp.route('/stats', methods=['GET'])
def get_training_stats():
    """📊 Obter estatísticas de treinamento"""
    try:
        stats = image_manager.get_training_stats()
        
        # Adicionar progresso detalhado por categoria
        detailed_progress = {}
        for category in stats.categories:
            detailed_progress[category] = image_manager.get_category_progress(category)
        
        return jsonify({
            "success": True,
            "data": {
                **stats.to_dict(),
                "detailed_progress": detailed_progress,
                "max_photos_per_class": TRAINING_CONFIG["max_photos_per_class"]
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@training_bp.route('/categories', methods=['GET'])
def get_training_categories():
    """📂 Listar categorias disponíveis"""
    try:
        categories = TRAINING_CONFIG["classes"]
        
        # Obter informações detalhadas de cada categoria
        categories_info = []
        for category in categories:
            progress = image_manager.get_category_progress(category)
            categories_info.append({
                "name": category,
                "display_name": category.replace("_", " ").title(),
                **progress
            })
        
        return jsonify({
            "success": True,
            "data": {
                "categories": categories_info,
                "total_categories": len(categories)
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@training_bp.route('/image/<category>/<filename>', methods=['DELETE'])
def delete_training_image(category, filename):
    """🗑️ Deletar imagem de treinamento"""
    try:
        success = image_manager.delete_image(category, filename)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Imagem {filename} removida com sucesso"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Falha ao remover imagem"
            }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@training_bp.route('/category/<category>/clear', methods=['POST'])
def clear_category_images(category):
    """🧹 Limpar todas as imagens de uma categoria"""
    try:
        # Validar categoria
        valid_categories = TRAINING_CONFIG["classes"]
        if category not in valid_categories:
            return jsonify({
                "success": False,
                "error": f"Categoria inválida. Categorias válidas: {valid_categories}"
            }), 400
        
        deleted_count = image_manager.clear_category(category)
        
        return jsonify({
            "success": True,
            "data": {
                "category": category,
                "deleted_count": deleted_count,
                "message": f"{deleted_count} imagens removidas de {category}"
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@training_bp.route('/clear-all', methods=['POST'])
def clear_all_training_data():
    """🧹 Limpar todos os dados de treinamento"""
    try:
        # Verificar se foi fornecida confirmação
        confirmation = request.json.get('confirm', False) if request.json else False
        
        if not confirmation:
            return jsonify({
                "success": False,
                "error": "Confirmação obrigatória. Envie {'confirm': true} no body da requisição"
            }), 400
        
        deleted_count = image_manager.clear_all_training_data()
        
        return jsonify({
            "success": True,
            "data": {
                "total_deleted": deleted_count,
                "message": f"Todos os dados de treinamento foram removidos ({deleted_count} imagens)"
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@training_bp.route('/export', methods=['GET'])
def export_training_data():
    """📦 Exportar dados de treinamento (metadata)"""
    try:
        stats = image_manager.get_training_stats()
        all_images = image_manager.get_all_training_images()
        
        export_data = {
            "export_timestamp": format_timestamp(),
            "stats": stats.to_dict(),
            "images": [img.to_dict() for img in all_images],
            "config": {
                "max_photos_per_class": TRAINING_CONFIG["max_photos_per_class"],
                "classes": TRAINING_CONFIG["classes"],
                "image_extensions": TRAINING_CONFIG["image_extensions"]
            }
        }
        
        return jsonify({
            "success": True,
            "data": export_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# 🛠️ Funções auxiliares
def format_timestamp(timestamp=None):
    """🕒 Formatar timestamp para string legível"""
    import datetime
    
    if timestamp is None:
        timestamp = datetime.datetime.now().timestamp()
    
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

# 🎯 Rotas de healthcheck
@training_bp.route('/health', methods=['GET'])
def training_health():
    """💓 Verificar saúde do serviço de treinamento"""
    try:
        stats = image_manager.get_training_stats()
        
        return jsonify({
            "success": True,
            "status": "healthy",
            "data": {
                "service": "training",
                "total_images": stats.total_images,
                "training_complete": stats.training_complete,
                "completion_percentage": stats.completion_percentage
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }), 500