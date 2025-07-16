🚀 Smart-Person-Detection-PLC: Sistema de Detecção e Telemetria de Pessoas com Integração Siemens S7-1500
🎯 Visão Geral do Projeto
Este projeto implementa um sistema de monitoramento computacional visionário em tempo real, focado na detecção de indivíduos e na extração de dados telemétricos (distância, velocidade). Ele estabelece uma interface de comunicação direta com Controladores Lógicos Programáveis (CLPs) Siemens S7-1500, utilizando a biblioteca Snap7, para a integração em ambientes de automação industrial e sistemas de segurança que demandam dados de presença humana precisos e acionáveis.

A solução emprega o modelo YOLOv8n para inferência de detecção de objetos e processamento de vídeo assíncrono, garantindo eficiência e responsividade. Os dados extraídos são serializados e transmitidos para um Data Block (DB) configurável no PLC, permitindo a lógica de controle programada com base em métricas ambientais.

✨ Funcionalidades Implementadas
Detecção de Pessoas em Tempo Real: Utiliza o modelo YOLOv8n (Ultralytics) otimizado para inferência de objetos da classe 'pessoa' (class ID: 0) em streams de vídeo RTSP.

Segmentação de Área de Interesse (AoI): Definição programática de uma área de monitoramento retangular centralizada no frame de vídeo, com filtragem de detecções fora da AoI.

Telemetria de Distância: Cálculo da distância euclidiana real (em centímetros) de indivíduos detectados em relação à câmera, empregando princípios de perspectiva baseados na altura em pixels e em um parâmetro de distância focal calibrável.

Estimativa de Velocidade: Implementação de um algoritmo de rastreamento de objetos por proximidade de centroides para cálculo da velocidade linear (em km/h) de indivíduos em movimento, utilizando a variação de posição no tempo.

Protocolo de Comunicação PLC Siemens (S7-1500):

Interface direta com CLPs Siemens S7-1500 através da biblioteca Snap7.

Mapeamento de dados estruturados para o Data Block DB17, conforme o seguinte esquema:

DB17.DBX0.0 (BOOL): Indicação de Pessoa_Detectada (presença de pelo menos um indivíduo na AoI).

DB17.DBW2 (INT): Quantidade_Pessoas (número total de indivíduos detectados).

DB17.DBD4 (REAL): Distancia_Minima (menor distância registrada entre as pessoas detectadas, em cm).

DB17.DBD8 (REAL): Velocidade_Maxima (maior velocidade registrada entre as pessoas detectadas, em km/h).

DB17.DBD12 (DINT): Timestamp_Unix (carimbo de tempo Unix da última atualização de dados).

DB17.DBX16.0 (BOOL): Sistema_Funcionando (sinal de heartbeat indicando operacionalidade do sistema).

Mecanismo de reconexão automática ao PLC para robustez da comunicação.

Otimização de Desempenho:

Arquitetura multi-threading para processamento de frames e inferência da IA em paralelo.

Estratégia de frame skipping configurável para gestão da carga computacional.

Filas de comunicação otimizadas (queue.Queue) entre as threads para gerenciamento de dados.

Visualização de Dados: Sobreposição de informações críticas (AoI, contagem, distância, velocidade) diretamente no stream de vídeo para depuração e monitoramento em tempo real.

🛠️ Pré-requisitos e Configuração
Requisitos de Software
Python 3.8+

Bibliotecas Python:

Bash

pip install opencv-python ultralytics python-snap7 numpy
Requisitos de Hardware
Câmera IP (RTSP): Compatível com stream RTSP para captura de vídeo.

Controlador Lógico Programável (PLC) Siemens S7-1500: Configurado para comunicação Ethernet/IP e com um Data Block (DB) acessível (DB17 é o padrão do projeto).

Conectividade de Rede: Rede IP configurada para permitir a comunicação entre a máquina host do sistema, a câmera RTSP e o PLC.

Configuração do Sistema
Clonagem do Repositório:

Bash

git clone https://github.com/SeuUsuario/Smart-Person-Detection-PLC.git
cd Smart-Person-Detection-PLC
Configuração do Stream RTSP:
No arquivo main.py, atualize a variável rtsp_url com o endpoint RTSP da sua câmera.

Python

rtsp_url = "rtsp://usuario:senha@IP_DA_CAMERA:PORTA/caminho_do_stream"
# Exemplo: "rtsp://DaniloLira:Danilo%4034333528@192.168.0.100:554/stream2"
Nota: Senhas com caracteres especiais devem ser URL-encoded.

Parâmetros de Conexão PLC:
Ajuste as variáveis self.plc_ip, self.plc_rack, self.plc_slot e self.db_number (padrão 17) na classe DetectorPessoasInteligente em main.py para corresponder à configuração do seu PLC Siemens S7-1500.

Habilitação de PUT/GET no PLC: É essencial que a comunicação PUT/GET esteja habilitada no PLC via TIA Portal. Esta configuração é encontrada em "Proteção e Segurança" -> "Mecanismos de conexão". Sem isso, a comunicação falhará.

Calibração da Distância Focal (focal_length):
Para garantir a precisão das medições de distância, é crucial calibrar o parâmetro self.focal_length.

Posicione um objeto (ou uma pessoa de altura conhecida self.altura_pessoa_real, ex: 170 cm) a uma distância conhecida da câmera.

Capture um frame e determine a altura do objeto em pixels (altura_pixels).

Calcule focal_length usando a relação: Focal_Length = (Altura_Pixels_Objeto * Distancia_Real_Objeto) / Altura_Real_Objeto.

Atualize self.focal_length na classe DetectorPessoasInteligente.

▶️ Execução
Para iniciar o sistema, execute o script principal:

Bash

python main.py
Uma janela de visualização será exibida, mostrando o stream de vídeo com as detecções e os dados sobrepostos. Mensagens de log serão impressas no console, incluindo o status da comunicação com o PLC e as métricas detectadas.

Controles de Operação:
ESC: Termina a execução do programa.

ESPAÇO: Alterna entre os estados de pausa e execução do processamento.

⚠️ Diagnóstico e Solução de Problemas
Falha na Conexão da Câmera: Verifique a sintaxe do rtsp_url, a conectividade de rede à câmera e se a câmera está ativa e transmitindo. Verifique portas de firewall.

Erro de Conexão com o PLC (snap7.snap7.Snap7Exception):

Confirme o IP do PLC (self.plc_ip).

Verifique o estado do PLC (deve estar em RUN).

Assegure a conectividade de rede (e.g., ping IP_DO_PLC).

CRÍTICO: Confirme que a opção PUT/GET está habilitada nas configurações de segurança do PLC no TIA Portal.

Medições de Distância/Velocidade Imprecisas: Reexecute o processo de calibração da self.focal_length com maior precisão.

Desempenho Lento (Baixo FPS):

Considere reduzir a resolução do stream RTSP da câmera.

Aumente o valor de self.frame_skip para processar menos frames.

Garanta que a máquina host possui recursos de CPU/GPU adequados para a inferência YOLO.

📧 Suporte e Contato
Para suporte técnico, questões ou sugestões, por favor, abra uma issue neste repositório GitHub ou entre em contato diretamente via e-mail: danilosilvalira10@hotmail.com

