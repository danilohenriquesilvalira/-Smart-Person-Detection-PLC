Ah, claro! Desculpe, aqui está o README completo em português para o seu projeto "Smart-Person-Detection-PLC":

Smart-Person-Detection-PLC
Visão Geral
O projeto Smart-Person-Detection-PLC é um sistema de vigilância inteligente, desenvolvido para detectar pessoas em tempo real através de um stream de câmera RTSP e comunicar dados relevantes diretamente com um PLC Siemens S7-1500 utilizando a biblioteca Snap7. Este sistema vai além da simples detecção, calculando a distância e velocidade reais dos indivíduos detectados, tornando-o extremamente valioso para diversas aplicações industriais e de segurança onde o monitoramento preciso da presença humana é crucial.

O coração do sistema emprega o modelo YOLOv8n para uma detecção de objetos eficiente, especificamente otimizado para pessoas. Dados como presença, contagem, distância mínima e velocidade máxima de pessoas dentro de uma área definida são transmitidos para o Data Block 17 (DB17) do PLC, permitindo respostas automatizadas e integração com sistemas de controle industrial.

Funcionalidades
Detecção de Pessoas em Tempo Real: Utiliza YOLOv8n para detecção precisa e rápida de pessoas em streams de vídeo RTSP ao vivo.

Monitoramento de Área Automatizado: Define automaticamente uma área de monitoramento central dentro da visão da câmera.

Cálculo de Distância Real: Estima a distância de indivíduos detectados da câmera em centímetros, com base na altura em pixels e numa distância focal calibrada.

Medição de Velocidade em Tempo Real: Calcula a velocidade de indivíduos em movimento em quilômetros por hora (km/h), fornecendo insights dinâmicos sobre o seu deslocamento.

Comunicação com PLC Siemens (S7-1500):

Integração direta com PLCs Siemens S7-1500 usando a biblioteca Snap7.

Transmite dados críticos para o DB17, incluindo:

BOOL (DBX0.0): Pessoa_Detectada (Presença de pessoas na área).

INT (DBW2): Quantidade_Pessoas (Contagem de pessoas).

REAL (DBD4): Distancia_Minima (Distância mínima de uma pessoa detectada).

REAL (DBD8): Velocidade_Maxima (Velocidade máxima de uma pessoa detectada).

DINT (DBD12): Timestamp_Unix (Carimbo de tempo Unix da última atualização).

BOOL (DBX16.0): Sistema_Funcionando (Status operacional do sistema, heartbeat).

Tentativas de reconexão automática do PLC para uma operação robusta.

Desempenho Otimizado:

Multi-threading para processamento de vídeo e inferência YOLO em paralelo.

Salto de frames (frame skipping) para gerenciar a carga de processamento e manter a responsividade.

Filas de dados otimizadas para garantir um fluxo de dados suave entre as threads.

Feedback Visual Intuitivo: Exibe indivíduos detectados, sua distância estimada e velocidade no feed de vídeo.

Exibição Compacta: Tela limpa e minimalista, focada nas informações visuais essenciais.

Requisitos
Antes de executar o projeto, certifique-se de ter o seguinte instalado:

Python 3.8+

OpenCV (cv2): Para captura e processamento de vídeo.

Ultralytics YOLO (ultralytics): Para o modelo YOLOv8.

Snap7 (python-snap7): Para comunicação com o PLC.

NumPy (numpy): Para operações numéricas.

Você pode instalar as dependências Python usando o pip:

Bash

pip install opencv-python ultralytics python-snap7 numpy
Requisitos de Hardware:
Câmera RTSP: Uma câmera de rede que forneça um stream RTSP.

PLC Siemens S7-1500: Configurado com um DB17 (Data Block 17) para troca de dados.

Conectividade de Rede: Certifique-se de que o seu ambiente Python possa alcançar tanto a câmera RTSP quanto o endereço IP do PLC.

Configuração
Clone o Repositório:

Bash

git clone https://github.com/SeuUsuario/Smart-Person-Detection-PLC.git
cd Smart-Person-Detection-PLC
Configuração da Câmera RTSP:
Abra o arquivo main.py e atualize a variável rtsp_url com o URL do stream RTSP da sua câmera.

Python

rtsp_url = "rtsp://DaniloLira:Danilo%4034333528@192.168.0.100:554/stream2"
Importante: Substitua DaniloLira:Danilo%4034333528 pelo nome de usuário e senha da sua câmera (com codificação URL), e 192.168.0.100:554/stream2 pelo endereço IP real e caminho do stream da sua câmera.

Configuração do PLC:
Certifique-se de que o seu PLC Siemens S7-1500 esteja acessível em 192.168.0.33 (ou ajuste self.plc_ip na classe DetectorPessoasInteligente).
O projeto assume um DB17 com a seguinte estrutura (ajuste self.db_number, self.plc_rack, self.plc_slot se necessário):

Endereço	Tipo de Dados	Descrição
DB17.DBX0.0	BOOL	Pessoa_Detectada
DB17.DBW2	INT	Quantidade_Pessoas
DB17.DBD4	REAL	Distancia_Minima
DB17.DBD8	REAL	Velocidade_Maxima
DB17.DBD12	DINT	Timestamp_Unix
DB17.DBX16.0	BOOL	Sistema_Funcionando

Exportar para as Planilhas
Nota sobre as configurações do PLC:

self.plc_rack = 0

self.plc_slot = 1 (Comum para S7-1500; verifique a sua configuração específica)

self.db_number = 17

Modelo YOLO:
O projeto faz o download automático do modelo yolov8n.pt se ele não estiver presente. Não é necessário fazer o download manual.

Calibração da Câmera (Distância Focal):
Para medições de distância precisas, você pode precisar calibrar o valor de self.focal_length. Este valor depende da lente e da resolução da sua câmera. Um método comum é:

Posicione um objeto com uma altura real conhecida (self.altura_pessoa_real, por exemplo, 170 cm) a uma distância conhecida da câmera.

Meça a altura desse objeto em pixels na tela (altura_pixels).

Calcule a distância focal: Focal_Length = (Altura_Pixels * Distancia_Real) / Altura_Real.
Ajuste self.focal_length no método __init__ de acordo.

Python

self.altura_pessoa_real = 170  # cm (padrão para uma pessoa média)
self.focal_length = 800  # Calibre este valor com base na sua câmera
Como Executar
Após configurar os pré-requisitos e as definições, execute o script main.py:

Bash

python main.py
O sistema será iniciado, tentará conectar-se à câmera e ao PLC, e então exibirá o feed de vídeo com as detecções.

Controles:
ESC: Sair da aplicação.

ESPAÇO: Pausar/Retomar o processamento e a exibição do vídeo.

Estrutura do Projeto
Smart-Person-Detection-PLC/
├── main.py                     # Script principal contendo a classe DetectorPessoasInteligente e a lógica de execução.
├── yolov8n.pt                  # Modelo YOLOv8 nano (baixado automaticamente pela ultralytics).
└── README.md                   # Este arquivo.
Resolução de Problemas
Stream is not opened ou Failed to connect camera:

Verifique novamente o seu rtsp_url para ter certeza de que está correto, incluindo nome de usuário, senha, IP, porta e caminho do stream.

Certifique-se de que sua câmera está ligada e acessível a partir da rede.

Verifique se nenhum firewall está bloqueando a porta RTSP (padrão 554).

Error connecting PLC:

Verifique o endereço IP do PLC (self.plc_ip).

Certifique-se de que o PLC está ligado e em modo RUN.

Verifique a conectividade de rede entre sua máquina e o PLC (ex: ping 192.168.0.33).

Confirme os números corretos de Rack e Slot para o seu PLC.

Assegure-se de que "Permitir acesso com comunicação PUT/GET de parceiro remoto (PLC, HMI, OPC UA, HTTP)" esteja ativado no projeto do seu PLC no TIA Portal, em "Proteção e Segurança" -> "Mecanismos de conexão".

Distância/Velocidade Imprecisa:

Recalibre self.focal_length cuidadosamente com base na configuração da sua câmera e no ambiente.

Certifique-se de que self.altura_pessoa_real é apropriado para a altura típica das pessoas que você espera detectar.

Problemas de Desempenho:

Se o FPS estiver muito baixo, considere reduzir self.frame_skip ou usar uma unidade de processamento mais potente.

Verifique se a resolução do seu stream RTSP não é excessivamente alta.

Melhorias Futuras
GUI para Configuração: Implementar uma interface gráfica de usuário para facilitar a configuração de URLs RTSP, definições do PLC e parâmetros de calibração.

Múltiplas Zonas de Detecção: Permitir que os usuários definam múltiplas zonas de detecção com formas personalizadas, em vez de apenas um retângulo central.

Rastreamento Avançado: Incorporar algoritmos de rastreamento de objetos mais sofisticados para melhorar a persistência de ID a longo prazo e cálculos de velocidade mais precisos em cenas com muitas pessoas.

Registro de Eventos (Event Logging): Implementar um registro detalhado de eventos em arquivos ou um banco de dados para análise e depuração posteriores.

Integração de Alarme: Acionar diretamente alarmes ou notificações com base em limites definidos (ex: pessoa muito próxima por muito tempo).

Licença
Este projeto é de código aberto e está disponível sob a Licença MIT.

Contato
Para quaisquer perguntas ou sugestões, por favor, abra uma issue neste repositório ou entre em contato com danilosilvalira10@hotmail.com
