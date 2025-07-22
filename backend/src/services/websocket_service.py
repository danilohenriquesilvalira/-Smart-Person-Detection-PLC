"""
🔧 Serviço WebSocket - Smart Detection Backend
"""
import asyncio
import websockets
import json
import threading
import time
import logging
from typing import Dict, Set, Callable, Optional

from config.settings import WEBSOCKET_CONFIG

# Configurar logging para reduzir spam
logging.getLogger('websockets').setLevel(logging.ERROR)

class WebSocketService:
    """🌐 Serviço WebSocket para comunicação em tempo real"""
    
    def __init__(self):
        self.host = WEBSOCKET_CONFIG["host"]
        self.port = WEBSOCKET_CONFIG["port"]
        self.max_clients = WEBSOCKET_CONFIG["max_clients"]
        
        # Estado do servidor
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.server = None
        self.running = False
        self.loop = None
        self.server_thread = None
        
        # Buffer de dados e callbacks
        self.data_buffer = {}
        self.last_data_sent = None
        self.command_callbacks: Dict[str, Callable] = {}
        
        print(f"🌐 Serviço WebSocket inicializado: ws://{self.host}:{self.port}")
    
    def set_command_callback(self, action: str, callback: Callable) -> None:
        """📝 Registrar callback para comando específico"""
        self.command_callbacks[action] = callback
        print(f"📝 Callback registrado para comando: {action}")
    
    def start_server(self) -> bool:
        """🚀 Iniciar servidor WebSocket"""
        if self.running:
            print("⚠️ Servidor WebSocket já está rodando")
            return True
        
        try:
            # Iniciar thread do servidor
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.name = "WebSocket-Server"
            self.server_thread.start()
            
            # Aguardar inicialização
            time.sleep(1.5)
            
            if self.running:
                print(f"🚀 Servidor WebSocket ativo em ws://{self.host}:{self.port}")
                return True
            else:
                print("❌ Falha ao iniciar servidor WebSocket")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao iniciar WebSocket: {e}")
            return False
    
    def stop_server(self) -> None:
        """🛑 Parar servidor WebSocket"""
        if not self.running:
            return
        
        try:
            self.running = False
            
            if self.server and hasattr(self, 'loop') and not self.loop.is_closed():
                # Fechar servidor no loop correto
                self.loop.call_soon_threadsafe(self.server.close)
            
            # Aguardar finalização
            time.sleep(1.0)
            
            print("🛑 Servidor WebSocket parado")
            
        except Exception as e:
            print(f"⚠️ Erro ao parar WebSocket: {e}")
    
    def _run_server(self) -> None:
        """🔄 Executar servidor em loop asyncio"""
        try:
            # Criar novo loop para thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Executar servidor
            self.loop.run_until_complete(self._start_websocket_server())
            
        except Exception as e:
            print(f"❌ Erro fatal no servidor WebSocket: {e}")
            self.running = False
        finally:
            # Limpar recursos
            if hasattr(self, 'loop') and not self.loop.is_closed():
                try:
                    self.loop.close()
                except:
                    pass
            print("🧹 Thread WebSocket finalizada")
    
    async def _start_websocket_server(self) -> None:
        """🌐 Inicializar servidor WebSocket"""
        try:
            # Configurações otimizadas
            self.server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port,
                ping_interval=30,      # Ping a cada 30 segundos
                ping_timeout=10,       # Timeout de 10 segundos
                close_timeout=5,       # Timeout para fechar conexão
                max_size=1024*1024,    # Max 1MB por mensagem
                max_queue=32,          # Max 32 mensagens em fila
                compression=None,      # Desabilitar compressão
                logger=None            # Desabilitar logs internos
            )
            
            self.running = True
            print(f"🎯 WebSocket aguardando conexões...")
            
            # Manter servidor ativo
            await self.server.wait_closed()
            
        except Exception as e:
            print(f"❌ Erro crítico no servidor WebSocket: {e}")
            self.running = False
    
    async def _handle_client(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """👤 Gerenciar cliente WebSocket"""
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        
        try:
            # Verificar limite de clientes
            if len(self.clients) >= self.max_clients:
                await websocket.close(code=1013, reason="Máximo de clientes atingido")
                return
            
            # Registrar cliente
            self.clients.add(websocket)
            print(f"🌐 Cliente conectado: {client_addr} (Total: {len(self.clients)})")
            
            # Enviar dados iniciais
            if self.data_buffer:
                try:
                    await websocket.send(json.dumps(self.data_buffer))
                    print(f"📤 Dados iniciais enviados para {client_addr}")
                except Exception as e:
                    print(f"⚠️ Erro enviando dados iniciais: {e}")
            
            # Loop principal de comunicação
            async for message in websocket:
                try:
                    await self._process_client_message(websocket, message, client_addr)
                except json.JSONDecodeError:
                    print(f"❌ JSON inválido de {client_addr}: {message}")
                except Exception as e:
                    print(f"❌ Erro processando mensagem de {client_addr}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            print(f"🔌 Cliente {client_addr} desconectou")
        except Exception as e:
            print(f"❌ Erro na conexão com {client_addr}: {e}")
        finally:
            # Remover cliente
            if websocket in self.clients:
                self.clients.remove(websocket)
            print(f"🗑️ Cliente {client_addr} removido (Total: {len(self.clients)})")
    
    async def _process_client_message(self, websocket: websockets.WebSocketServerProtocol, 
                                     message: str, client_addr: str) -> None:
        """📨 Processar mensagem do cliente"""
        try:
            # Parse da mensagem
            cmd = json.loads(message)
            action = cmd.get('action', '')
            
            print(f"📨 Comando de {client_addr}: {action}")
            
            # Executar callback se existir
            if action in self.command_callbacks:
                try:
                    result = self.command_callbacks[action](cmd)
                    
                    # Enviar resposta se necessário
                    response = {
                        "type": "command_response",
                        "action": action,
                        "success": bool(result),
                        "timestamp": time.time()
                    }
                    
                    await websocket.send(json.dumps(response))
                    
                    if result:
                        print(f"✅ Comando '{action}' executado com sucesso")
                    else:
                        print(f"⚠️ Comando '{action}' falhou")
                        
                except Exception as e:
                    print(f"❌ Erro executando callback '{action}': {e}")
                    
                    # Enviar erro
                    error_response = {
                        "type": "command_error",
                        "action": action,
                        "error": str(e),
                        "timestamp": time.time()
                    }
                    
                    await websocket.send(json.dumps(error_response))
            else:
                print(f"❓ Comando desconhecido: {action}")
                
        except Exception as e:
            print(f"❌ Erro processando comando: {e}")
    
    def update_data(self, data: Dict) -> None:
        """🔄 Atualizar dados para broadcast"""
        # Verificar se dados realmente mudaram
        data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        
        if data_str == self.last_data_sent:
            return  # Não enviar dados duplicados
        
        self.data_buffer = data
        self.last_data_sent = data_str
        
        # Agendar broadcast se servidor estiver ativo
        if self.running and self.clients and hasattr(self, 'loop') and not self.loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(
                    self._broadcast_data(data),
                    self.loop
                )
            except Exception as e:
                print(f"❌ Erro agendando broadcast: {e}")
    
    async def _broadcast_data(self, data: Dict) -> None:
        """📡 Broadcast dados para todos os clientes"""
        if not self.clients:
            return
        
        message = json.dumps(data, separators=(',', ':'))
        disconnected_clients = set()
        sent_count = 0
        
        # Enviar para todos os clientes
        for client in list(self.clients):  # Cópia para evitar modificação durante iteração
            try:
                await asyncio.wait_for(client.send(message), timeout=1.0)
                sent_count += 1
            except asyncio.TimeoutError:
                print("⏱️ Timeout enviando para cliente")
                disconnected_clients.add(client)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                print(f"❌ Erro enviando para cliente: {e}")
                disconnected_clients.add(client)
        
        # Remover clientes desconectados
        self.clients -= disconnected_clients
        
        if sent_count > 0:
            print(f"📡 Dados enviados para {sent_count} cliente(s)")
        
        if disconnected_clients:
            print(f"🧹 {len(disconnected_clients)} clientes desconectados removidos")
    
    def send_message_to_client(self, websocket: websockets.WebSocketServerProtocol, message: Dict) -> bool:
        """📤 Enviar mensagem para cliente específico"""
        if not self.running or websocket not in self.clients:
            return False
        
        try:
            message_str = json.dumps(message, separators=(',', ':'))
            asyncio.run_coroutine_threadsafe(
                websocket.send(message_str),
                self.loop
            )
            return True
        except Exception as e:
            print(f"❌ Erro enviando mensagem para cliente: {e}")
            return False
    
    def broadcast_notification(self, notification: Dict) -> None:
        """📢 Enviar notificação para todos os clientes"""
        notification_data = {
            "type": "notification",
            "timestamp": time.time(),
            **notification
        }
        
        self.update_data(notification_data)
    
    def get_status(self) -> Dict:
        """📊 Obter status do servidor"""
        return {
            "running": self.running,
            "clients_connected": len(self.clients),
            "host": self.host,
            "port": self.port,
            "max_clients": self.max_clients,
            "has_loop": hasattr(self, 'loop') and self.loop is not None,
            "loop_closed": hasattr(self, 'loop') and self.loop.is_closed() if hasattr(self, 'loop') else True,
            "has_server": self.server is not None,
            "has_data": bool(self.data_buffer),
            "registered_commands": list(self.command_callbacks.keys())
        }
    
    def get_connected_clients_info(self) -> list:
        """👥 Obter informações dos clientes conectados"""
        clients_info = []
        
        for client in self.clients:
            try:
                clients_info.append({
                    "address": f"{client.remote_address[0]}:{client.remote_address[1]}",
                    "state": str(client.state),
                    "ping": getattr(client, 'ping', None)
                })
            except Exception as e:
                print(f"⚠️ Erro obtendo info do cliente: {e}")
        
        return clients_info
    
    def ping_all_clients(self) -> None:
        """🏓 Ping todos os clientes"""
        if not self.running or not self.clients:
            return
        
        ping_data = {
            "type": "ping",
            "timestamp": time.time(),
            "server": "smart_detection"
        }
        
        self.update_data(ping_data)
    
    def __del__(self):
        """🧹 Limpeza na destruição"""
        self.stop_server()

# 🏭 Instância global do serviço WebSocket
websocket_service = WebSocketService()