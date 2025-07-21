import asyncio
import websockets
import json
import threading
import time
import logging

# Configurar logging para reduzir spam
logging.getLogger('websockets').setLevel(logging.ERROR)

class WebSocketServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.server = None
        self.running = False
        self.data_buffer = {}
        self.last_data_sent = None
        self.command_callbacks = {}
        
    def set_command_callback(self, action, callback):
        """Definir callback para comandos específicos"""
        self.command_callbacks[action] = callback
        
    async def register_client(self, websocket):
        """Registrar novo cliente com tratamento robusto de erros"""
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        
        try:
            self.clients.add(websocket)
            print(f"🌐 Cliente conectado: {client_addr} (Total: {len(self.clients)})")
            
            # Enviar dados iniciais imediatamente
            if self.data_buffer:
                try:
                    await websocket.send(json.dumps(self.data_buffer))
                    print(f"📤 Dados iniciais enviados para {client_addr}")
                except:
                    print(f"❌ Falha ao enviar dados iniciais para {client_addr}")
            
            # Loop principal de escuta
            try:
                async for message in websocket:
                    try:
                        # Processar comando recebido
                        cmd = json.loads(message)
                        print(f"📨 Comando de {client_addr}: {cmd}")
                        
                        # Executar callback se existir
                        action = cmd.get('action', '')
                        if action in self.command_callbacks:
                            try:
                                result = self.command_callbacks[action](cmd)
                                if result:
                                    print(f"✅ Comando '{action}' executado com sucesso")
                            except Exception as e:
                                print(f"❌ Erro executando callback '{action}': {e}")
                        else:
                            await self.process_command(cmd)
                            
                    except json.JSONDecodeError:
                        print(f"❌ JSON inválido de {client_addr}: {message}")
                    except Exception as e:
                        print(f"❌ Erro processando mensagem de {client_addr}: {e}")
                        
            except websockets.exceptions.ConnectionClosed:
                print(f"🔌 Cliente {client_addr} desconectou normalmente")
            except websockets.exceptions.ConnectionClosedError:
                print(f"🔌 Conexão com {client_addr} perdida")
            except Exception as e:
                print(f"❌ Erro na conexão com {client_addr}: {e}")
                
        finally:
            # Sempre remover cliente da lista
            if websocket in self.clients:
                self.clients.remove(websocket)
            print(f"🗑️ Cliente {client_addr} removido (Total: {len(self.clients)})")
    
    async def process_command(self, cmd):
        """Processar comandos recebidos (fallback)"""
        action = cmd.get('action', '')
        
        if action == 'train':
            print("🎯 Comando: Iniciar treinamento")
        elif action == 'detect':
            print("🎯 Comando: Iniciar detecção")
        elif action == 'reset':
            print("🎯 Comando: Reset sistema")
        elif action == 'ping':
            print("🏓 Ping recebido")
        else:
            print(f"❓ Comando desconhecido: {action}")
    
    async def broadcast_data(self, data):
        """Enviar dados para todos os clientes com retry"""
        if not self.clients:
            return
        
        message = json.dumps(data, separators=(',', ':'))  # JSON compacto
        disconnected = set()
        sent_count = 0
        
        for client in list(self.clients):  # Cópia da lista para evitar modificação durante iteração
            try:
                await asyncio.wait_for(client.send(message), timeout=1.0)  # Timeout de 1 segundo
                sent_count += 1
            except asyncio.TimeoutError:
                print(f"⏱️ Timeout enviando para cliente")
                disconnected.add(client)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                print(f"❌ Erro enviando para cliente: {e}")
                disconnected.add(client)
        
        # Remover clientes desconectados
        self.clients -= disconnected
        
        if sent_count > 0:
            print(f"📡 Dados enviados para {sent_count} cliente(s)")
        
        if disconnected:
            print(f"🧹 Removidos {len(disconnected)} clientes desconectados")
    
    def update_data(self, data):
        """Atualizar dados do buffer de forma thread-safe"""
        # Verificar se dados realmente mudaram
        data_str = json.dumps(data, sort_keys=True)
        if data_str == self.last_data_sent:
            return  # Não enviar dados duplicados
        
        self.data_buffer = data
        self.last_data_sent = data_str
        
        # Enviar para clientes apenas se houver clientes conectados
        if self.running and self.clients and hasattr(self, 'loop'):
            try:
                if not self.loop.is_closed():
                    # Agendar envio no loop principal
                    future = asyncio.run_coroutine_threadsafe(
                        self.broadcast_data(data), 
                        self.loop
                    )
                    # Não aguardar completar para não bloquear
                    
            except Exception as e:
                print(f"❌ Erro agendando envio de dados: {e}")
    
    def start_server(self):
        """Iniciar servidor WebSocket em thread separada"""
        def run_server():
            try:
                # Criar novo loop para a thread
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                
                async def start_websocket_server():
                    try:
                        # Configurações otimizadas para estabilidade
                        self.server = await websockets.serve(
                            self.register_client,
                            self.host, 
                            self.port,
                            ping_interval=30,      # Ping a cada 30 segundos
                            ping_timeout=10,       # Timeout de 10 segundos  
                            close_timeout=5,       # Timeout para fechar conexão
                            max_size=1024*1024,    # Max 1MB por mensagem
                            max_queue=32,          # Max 32 mensagens em fila
                            compression=None,      # Desabilitar compressão para simplicidade
                            logger=None            # Desabilitar logs internos
                        )
                        
                        self.running = True
                        print(f"🚀 WebSocket servidor iniciado!")
                        print(f"📍 Endereço: ws://{self.host}:{self.port}")
                        print(f"🔄 Aguardando conexões...")
                        
                        # Manter servidor rodando
                        await self.server.wait_closed()
                        
                    except Exception as e:
                        print(f"💥 Erro crítico no servidor WebSocket: {e}")
                        self.running = False
                
                # Executar servidor
                self.loop.run_until_complete(start_websocket_server())
                
            except Exception as e:
                print(f"💥 Erro fatal no loop WebSocket: {e}")
                self.running = False
            finally:
                # Limpar recursos
                if hasattr(self, 'loop') and not self.loop.is_closed():
                    try:
                        self.loop.close()
                    except:
                        pass
                print("🛑 Thread do WebSocket finalizada")
        
        # Iniciar thread do servidor
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.name = "WebSocket-Server"
        self.thread.start()
        
        # Aguardar inicialização
        time.sleep(1.5)
        
        return self.running
    
    def stop_server(self):
        """Parar servidor graciosamente"""
        if self.running and hasattr(self, 'server'):
            try:
                print("🛑 Parando servidor WebSocket...")
                
                if hasattr(self, 'loop') and not self.loop.is_closed():
                    # Fechar servidor no loop correto
                    self.loop.call_soon_threadsafe(self.server.close)
                    
                self.running = False
                
                # Aguardar um pouco para finalização
                time.sleep(1.0)
                
                print("✅ Servidor WebSocket parado")
                
            except Exception as e:
                print(f"❌ Erro ao parar servidor: {e}")
    
    def get_client_count(self):
        """Retornar número de clientes conectados"""
        return len(self.clients)
    
    def is_running(self):
        """Verificar se servidor está rodando"""
        return (self.running and 
                hasattr(self, 'loop') and 
                hasattr(self, 'server') and 
                not self.loop.is_closed())
    
    def get_status(self):
        """Obter status detalhado do servidor"""
        return {
            "running": self.running,
            "clients": len(self.clients),
            "has_loop": hasattr(self, 'loop'),
            "loop_closed": hasattr(self, 'loop') and self.loop.is_closed(),
            "has_server": hasattr(self, 'server'),
            "has_data": bool(self.data_buffer),
            "host": self.host,
            "port": self.port
        }

# Estrutura de dados padrão
def create_data_structure(status="AGUARDANDO", estado="SEM_COPO", valores=None, contadores=None, plc_status=None, sensibilidade=0.1):
    """Criar estrutura de dados padrão para WebSocket"""
    return {
        "timestamp": time.time(),
        "status": status,
        "estado_detectado": estado,
        "valores": valores or {
            "sem_copo": 0.0,
            "copo_bom": 0.0,
            "copo_danificado": 0.0
        },
        "contadores": contadores or {
            "sem_copo": 0,
            "copo_bom": 0,
            "copo_danificado": 0
        },
        "sensibilidade": sensibilidade,
        "treinamento_completo": False,
        "plc": plc_status or {
            "conectado": False,
            "db18_disponivel": False
        }
    }

# Classe para gerenciar comandos do frontend
class CommandHandler:
    def __init__(self):
        self.commands = []
        
    def handle_train(self, cmd):
        print("🎓 Executando comando de treinamento...")
        self.commands.append(('train', time.time()))
        return True
        
    def handle_detect(self, cmd):
        print("🎯 Executando comando de detecção...")
        self.commands.append(('detect', time.time()))
        return True
        
    def handle_reset(self, cmd):
        print("🔄 Executando comando de reset...")
        self.commands.append(('reset', time.time()))
        return True
    
    def get_last_commands(self, limit=5):
        return self.commands[-limit:]

# Exemplo de uso integrado
class DetectorWebSocket:
    def __init__(self):
        self.websocket_server = WebSocketServer()
        self.command_handler = CommandHandler()
        self.setup_callbacks()
        
    def setup_callbacks(self):
        """Configurar callbacks de comandos"""
        self.websocket_server.set_command_callback('train', self.command_handler.handle_train)
        self.websocket_server.set_command_callback('detect', self.command_handler.handle_detect)
        self.websocket_server.set_command_callback('reset', self.command_handler.handle_reset)
        
    def start(self):
        """Iniciar sistema completo"""
        print("🚀 Iniciando sistema WebSocket...")
        
        if self.websocket_server.start_server():
            print("✅ Sistema WebSocket online!")
            return True
        else:
            print("❌ Falha ao iniciar sistema WebSocket!")
            return False
    
    def send_detection_data(self, valores, contadores, status="DETECCAO", estado="SEM_COPO", plc_connected=False):
        """Enviar dados de detecção"""
        data = create_data_structure(
            status=status,
            estado=estado,
            valores=valores,
            contadores=contadores,
            plc_status={
                "conectado": plc_connected,
                "db18_disponivel": plc_connected
            }
        )
        
        self.websocket_server.update_data(data)
        
    def stop(self):
        """Parar sistema"""
        self.websocket_server.stop_server()

# Teste robusto
if __name__ == "__main__":
    print("🧪 === TESTE ROBUSTO DO WEBSOCKET SERVER ===")
    
    # Criar sistema integrado
    detector = DetectorWebSocket()
    
    try:
        # Iniciar sistema
        if detector.start():
            print("🎉 Sistema iniciado com sucesso!")
            print("📱 Abra o frontend React em http://localhost:5173")
            print("🔗 WebSocket disponível em ws://localhost:8765")
            print()
            
            # Simular dados realistas por 30 segundos
            for i in range(15):
                # Simular valores de detecção mais realistas
                valores = {
                    "sem_copo": 0.1 + (i % 3) * 0.05,
                    "copo_bom": 0.7 + (i % 4) * 0.08,
                    "copo_danificado": 0.2 + (i % 2) * 0.03
                }
                
                contadores = {
                    "sem_copo": min(i // 3, 10),
                    "copo_bom": min(i // 2, 10), 
                    "copo_danificado": min(i // 5, 10)
                }
                
                status = ["AGUARDANDO", "TREINAMENTO", "DETECCAO"][i % 3]
                estado = ["SEM_COPO", "COPO_BOM", "COPO_DANIFICADO"][i % 3]
                
                detector.send_detection_data(
                    valores=valores,
                    contadores=contadores,
                    status=status,
                    estado=estado,
                    plc_connected=(i % 4 == 0)
                )
                
                print(f"📡 Ciclo {i+1}/15 - Status: {status} - Clientes: {detector.websocket_server.get_client_count()}")
                
                time.sleep(2)
            
            print("\n⏱️ Mantendo servidor ativo por mais 30 segundos...")
            print("💡 Teste os botões no frontend!")
            
            # Manter ativo para testes manuais
            for i in range(30):
                time.sleep(1)
                if i % 5 == 0:
                    status = detector.websocket_server.get_status()
                    print(f"📊 Status: {status['clients']} clientes - Running: {status['running']}")
            
        else:
            print("💥 Falha ao iniciar sistema!")
            
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário")
        
    finally:
        print("🛑 Parando sistema...")
        detector.stop()
        print("✅ Sistema finalizado!")

    print("\n🏁 Teste concluído!")