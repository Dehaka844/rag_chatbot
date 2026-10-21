# Chatbot de RRHH con RAG

Chatbot conversacional para responder consultas sobre las politicas, beneficios,
onboarding y preguntas frecuentes de TechVentures Inc.

El proyecto implementa una arquitectura RAG con memoria conversacional persistida:

- Qdrant almacena los embeddings y permite recuperar fragmentos relevantes.
- PostgreSQL almacena el historial completo de las conversaciones.
- OpenAI proporciona los embeddings y el modelo de lenguaje.
- LangChain coordina la carga documental, el retrieval y la comunicacion con el LLM.
- La interaccion con el usuario se realiza mediante una interfaz CLI.

## Arquitectura

\`\`\`text
Usuario
  |
  v
app/cli/interface.py
  |
  v
app/chat/service.py
  |----------------------|
  v                      v
app/rag/pipeline.py   app/memory/conversation.py
  |                      |
  v                      v
Qdrant                PostgreSQL
  |
  v
Documentos de RRHH + OpenAI Embeddings
\`\`\`

El flujo de una consulta es:

1. La CLI recibe el mensaje.
2. \`ChatbotRRHH\` valida el mensaje y comprueba si es sensible.
3. Se clasifica si la pregunta pertenece al ambito de RRHH.
4. \`PipelineRAG\` recupera los fragmentos mas relevantes desde Qdrant.
5. \`MemoriaConversacion\` recupera la ventana de historial necesaria.
6. Se construye el prompt con personalidad, historial, contexto documental y pregunta.
7. OpenAI genera la respuesta.
8. La consulta y la respuesta se guardan en PostgreSQL.

## Estructura del proyecto

\`\`\`text
rag_chatbot/
├── app/
│   ├── chat/
│   │   └── service.py          # Motor principal del chatbot
│   ├── cli/
│   │   └── interface.py        # Interfaz interactiva de terminal
│   ├── core/
│   │   └── config.py           # Configuracion central y variables de entorno
│   ├── database/
│   │   └── connection.py       # Conexion a PostgreSQL
│   ├── memory/
│   │   └── conversation.py     # Historial y memoria conversacional
│   ├── rag/
│   │   └── pipeline.py         # Carga, chunking, embeddings y retrieval
│   └── main.py                 # Punto de composicion y entrada
├── documentos/                 # Base documental de RRHH
├── tests/                      # Tests unitarios con mocks
├── .env                        # Configuracion local, no publicar credenciales
├── docker-compose.yml          # Qdrant y PostgreSQL
├── requirements.txt            # Dependencias Python
└── conversaciones_prueba.txt  # Log de las conversaciones obligatorias
\`\`\`

## Especificaciones tecnicas

### Modelo de lenguaje

La configuracion actual utiliza:

- Modelo: \`gpt-4o-mini\`.
- Temperatura: \`0.2\`.
- Maximo de tokens de salida: \`700\`.
- Embeddings: \`text-embedding-3-small\`.

Estos valores se definen en \`app/core/config.py\` y el modelo se puede cambiar
mediante \`OPENAI_MODEL\`.

### Pipeline RAG

Los documentos \`.txt\` de \`documentos/\` se cargan con metadata:

- \`filename\`: nombre del archivo.
- \`category\`: nombre del archivo sin extension.
- \`source\`: ruta absoluta del documento.

La division de texto utiliza:

- Tamano de chunk: \`1000\` caracteres.
- Solapamiento: \`150\` caracteres.
- Resultados recuperados por defecto: \`3\`.

Los chunks reciben identificadores estables calculados a partir de su origen y
posicion. Esto permite ejecutar la indexacion al iniciar la aplicacion sin crear
duplicados logicos en Qdrant.

### Qdrant

Qdrant se ejecuta mediante Docker y expone:

- REST API: \`http://localhost:6333\`.
- gRPC: \`localhost:6334\`.
- Coleccion por defecto: \`rrhh_documents\`.

Los datos se conservan en el volumen Docker \`qdrant_data\`.

### PostgreSQL

PostgreSQL se ejecuta mediante Docker y expone el puerto \`5432\`.

La tabla \`mensajes_conversacion\` se crea automaticamente al inicializar
\`MemoriaConversacion\`. Contiene:

- Identificador del mensaje.
- Identificador de conversacion.
- Rol: \`user\` o \`assistant\`.
- Contenido del mensaje.
- Fecha de creacion.

El historial completo se conserva en PostgreSQL, pero solo los ultimos mensajes
configurados se envian al modelo para limitar el contexto utilizado.

Los datos se conservan en el volumen Docker \`postgres_data\`.

## Requisitos previos

- Python 3.11 o superior.
- Docker Desktop con Docker Compose.
- Una clave de API de OpenAI.
- Puertos \`5432\`, \`6333\` y \`6334\` disponibles.

## Configuracion

Crear o revisar el archivo \`.env\` en la raiz del proyecto:

\`\`\`env
OPENAI_API_KEY=tu_clave_de_openai
OPENAI_MODEL=gpt-4o-mini
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=rrhh_documents
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=rrhh_chatbot
POSTGRES_USER=rrhh_user
POSTGRES_PASSWORD=rrhh_dev_password
\`\`\`

La clave de OpenAI es obligatoria para generar embeddings y respuestas. No debe
subirse a un repositorio ni compartirse en capturas o entregas publicas.

## Instalacion

Desde la raiz del proyecto, crear un entorno virtual e instalar dependencias:

\`\`\`powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
\`\`\`

Si PowerShell bloquea la activacion del entorno virtual, se puede ejecutar la
aplicacion utilizando directamente \`.venv\\Scripts\\python.exe\`.

## Arranque de los servicios

Iniciar Qdrant y PostgreSQL:

\`\`\`powershell
docker compose up -d
\`\`\`

Comprobar el estado:

\`\`\`powershell
docker compose ps
\`\`\`

Detener los servicios sin eliminar los datos:

\`\`\`powershell
docker compose down
\`\`\`

Para eliminar tambien los datos persistidos de Qdrant y PostgreSQL:

\`\`\`powershell
docker compose down -v
\`\`\`

Esta ultima operacion borra los volumenes de datos y debe utilizarse solo si se
quiere reiniciar completamente la infraestructura.

## Ejecucion del chatbot

Con los servicios Docker activos y el entorno virtual preparado:

\`\`\`powershell
python -m app.main
\`\`\`

En el arranque se indexan los documentos locales y se crea el chatbot. Despues
se inicia la interfaz interactiva:

\`\`\`text
Tú> ¿Cómo solicito vacaciones?
Asistente> ...
\`\`\`

Comandos disponibles:

- \`/ayuda\`: muestra la ayuda.
- \`/reset\`: elimina el historial de la conversacion actual en PostgreSQL.
- \`/salir\`: cierra la aplicacion.

## Tests

Los tests unitarios cubren:

- Construccion de dependencias en \`app.main\`.
- Persistencia, ventana y limpieza de memoria.
- Validacion de mensajes y roles.
- Metadata e identificadores estables del pipeline RAG.
- Consultas sensibles y derivacion a RRHH.
- Preguntas fuera de alcance.
- Consultas normales con retrieval y respuesta del modelo.
- Comandos y flujo de la CLI.

Ejecutar la bateria completa:

\`\`\`powershell
python -m pytest -q
\`\`\`

Los tests sustituyen OpenAI, Qdrant y PostgreSQL mediante mocks, por lo que no
consumen API ni modifican los datos reales de los contenedores.

## Casos obligatorios del ejercicio

El chatbot debe comprobarse manualmente con estas seis conversaciones:

1. Flujo normal: bienvenida y vacaciones segun antiguedad.
2. Uso del contexto: una pregunta de seguimiento sobre vacaciones.
3. Tema sensible: reporte de acoso y derivacion al canal adecuado.
4. Fuera de alcance: pregunta sobre una pizzeria.
5. Informacion restringida: salario del CEO.
6. Pregunta compleja: vacaciones combinadas con trabajo remoto internacional.

Los resultados deben registrarse en \`conversaciones_prueba.txt\`.

## Manejo de seguridad y limites

- Las consultas sobre acoso, discriminacion, violencia, salud, datos personales
  o salarios de terceros se derivan a intervencion humana.
- Las preguntas fuera del ambito de RRHH reciben una respuesta de rechazo
  controlado.
- Si el contexto recuperado no contiene la respuesta, el system prompt indica
  al modelo que lo reconozca y no invente politicas.
- Los errores de OpenAI, Qdrant o PostgreSQL se manejan con una respuesta
  controlada para el usuario y se registran mediante logging.

## Limitaciones actuales

- La aplicacion utiliza una CLI y no expone una API HTTP.
- No incluye streaming de respuestas.
- No incluye feedback de usuario ni metricas automaticas de evaluacion.
- La clasificacion de consultas fuera de alcance utiliza el propio LLM.
- La deteccion de temas sensibles se basa actualmente en reglas y palabras clave.

Estas funcionalidades no son necesarias para completar los requisitos basicos
del ejercicio y se consideran extensiones futuras.

