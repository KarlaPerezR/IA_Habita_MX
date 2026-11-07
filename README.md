# Habita MX · Fase 3

Sistema multiagente académico para evaluar alternativas de vivienda y escenarios de financiamiento. Utiliza **Python 3.11, CrewAI y Ollama local** con cuatro agentes: Perfil del Usuario, Evaluación de Zona, Financiero y Coordinador. Built with Llama.

Esta guía explica cómo trabajar desde **Visual Studio Code en Windows**, con Anaconda para administrar Python y PowerShell como terminal integrada. El catálogo contiene seis zonas ficticias y condiciones financieras simuladas.

## 1. Preparar Visual Studio Code

Necesitas estos componentes:

| Componente | Uso |
|---|---|
| [Visual Studio Code](https://code.visualstudio.com/) | Editar y ejecutar el proyecto. |
| Anaconda o Miniconda | Administrar el ambiente de Python 3.11. |
| [Ollama](https://ollama.com/download) | Ejecutar el modelo de lenguaje local. |
| Extensión **Python**, de Microsoft (`ms-python.python`) | Seleccionar el intérprete y ejecutar scripts. |
| Extensión **Jupyter**, de Microsoft (`ms-toolsai.jupyter`) | Ejecutar el cuaderno dentro de VS Code. |

Abre el panel de extensiones con **Ctrl + Shift + X** e instala Python y Jupyter si todavía no aparecen instaladas.

En **Archivo → Abrir carpeta**, selecciona la carpeta que contiene `main.py`, `environment.yml` y `Habita_MX.ipynb`. Si descargaste el ZIP, extráelo primero y abre la carpeta `habita-mx` que está dentro.

Abre **Terminal → Nueva terminal** y elige **PowerShell**. Los comandos de esta guía se ejecutan desde la carpeta del proyecto. Comprueba la ubicación:

```powershell
Get-Location
Test-Path .\main.py
```

El segundo comando debe devolver `True`. Si devuelve `False`, abre la carpeta correcta antes de continuar.

## 2. Preparar el ambiente de Anaconda

Comprueba los ambientes disponibles:

```powershell
conda env list
```

**Si aparece `habita-mx`, úsalo directamente.** Si no aparece, créalo una sola vez:

```powershell
conda env create -f environment.yml
```

Este archivo crea el ambiente `habita-mx` con Python 3.11 e instala las dependencias de `requirements.txt`. La instalación inicial requiere internet. [Documentación de Conda](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html).

Verifica el intérprete y la instalación de CrewAI:

```powershell
conda run -n habita-mx python -c "import sys; from importlib.metadata import version; print(sys.executable); print('CrewAI:', version('crewai'))"
```

Si aparece `PackageNotFoundError` para CrewAI, el ambiente existe pero le faltan dependencias. Complétalas y repite la comprobación:

```powershell
conda run --no-capture-output -n habita-mx python -m pip install -r requirements.txt
```

Conserva la ruta de `python.exe` que imprime la comprobación: la usarás en el siguiente paso. `requirements-lock.txt` registra las versiones exactas de la demostración original en Windows.

### Si PowerShell no reconoce conda

Para una instalación estándar de Anaconda del usuario actual, puedes invocarlo por su ruta:

```powershell
$habitaConda = Join-Path $env:USERPROFILE "anaconda3\Scripts\conda.exe"
Test-Path $habitaConda
& $habitaConda env list
```

Si la comprobación devuelve `True`, sustituye `conda` por `& $habitaConda` en los comandos de esta guía. Por ejemplo:

```powershell
& $habitaConda run --no-capture-output -n habita-mx python main.py --diagnostico
```

Si devuelve `False`, localiza tu instalación de Anaconda o Miniconda y asigna a `$habitaConda` la ruta de su archivo `Scripts\conda.exe`. La carpeta puede variar según la instalación.

## 3. Seleccionar el intérprete en VS Code

1. Abre `main.py` en el editor.
2. Presiona **Ctrl + Shift + P**.
3. Ejecuta **Python: Select Interpreter / Python: Seleccionar intérprete**.
4. Selecciona el ambiente **habita-mx**, con Python 3.11.

Si no aparece, utiliza **Enter interpreter path / Introducir ruta del intérprete** y pega la ruta de `python.exe` obtenida en el paso anterior. El intérprete seleccionado se utiliza para las funciones de Python del editor, la ejecución y la depuración. [Documentación de VS Code](https://code.visualstudio.com/docs/python/environments).

Los comandos de esta guía usan `conda run -n habita-mx`, que elige explícitamente el ambiente aunque PowerShell no lo active automáticamente. Si prefieres activarlo, ejecuta `conda activate habita-mx` y después utiliza `python` directamente.

## 4. Comprobar Ollama y el modelo

Abre la aplicación **Ollama** y mantenla funcionando. En la terminal de VS Code consulta los modelos instalados:

```powershell
ollama list
```

Debe aparecer `llama3.2:latest`. Si falta, descárgalo:

```powershell
ollama pull llama3.2
```

Comprueba la conexión del proyecto:

```powershell
conda run --no-capture-output -n habita-mx python main.py --diagnostico
```

Una respuesta correcta muestra el modelo, su digest, las versiones de Python, CrewAI y Ollama, y la dirección local `http://127.0.0.1:11434`.

Si Ollama no responde, ejecuta `ollama serve` en **otra terminal** y déjala abierta. Si el puerto ya está ocupado, puede que el servidor esté iniciado: vuelve a probar el diagnóstico.

## 5. Ejecutar los cuatro agentes

Desde la terminal integrada de VS Code:

```powershell
conda run --no-capture-output -n habita-mx python main.py --modo crew
```

El flujo es **Perfil → Zona → Financiero → Coordinador**. Verás mensajes de herramientas utilizadas y tareas completadas. La ejecución puede tardar desde decenas de segundos hasta varios minutos, según el equipo.

Al terminar, la terminal muestra el resultado y la ruta donde se guardó la evidencia. Cada corrida crea una carpeta nueva dentro de `salidas/`.

Para las siguientes sesiones, abre el proyecto en VS Code, inicia Ollama y ejecuta el comando anterior.

### Consultar los resultados

En el explorador de VS Code, abre la carpeta de la corrida dentro de `salidas/`:

| Archivo | Contenido |
|---|---|
| `reporte.md` | Ranking explicado, alertas y alternativas descartadas. |
| `resultado.json` | Resultado consolidado, duración y metadatos. |
| `interacciones.jsonl` | Herramientas utilizadas, validaciones y conclusiones breves. |
| `perfil.json`, `zonas.json`, `finanzas.json`, `coordinacion.json` | Salidas aceptadas de cada tarea. |
| `calculos.json` | Evidencia numérica de todas las etapas. |
| `entrada_perfil.json`, `entrada_zonas.csv` | Copias de las entradas utilizadas. |

Para leer `reporte.md` con formato, ábrelo y presiona **Ctrl + Shift + V**. Si una corrida falla, consulta `error.json` en su carpeta; esa corrida no produce un resultado final exitoso.

## 6. Ejecutar el cuaderno Jupyter en VS Code

1. Abre `Habita_MX.ipynb` desde el explorador del editor.
2. Pulsa **Select Kernel / Seleccionar kernel**, arriba a la derecha.
3. Elige el ambiente **habita-mx**. Si hace falta, abre **Select Another Kernel / Seleccionar otro kernel → Python Environments / Ambientes de Python**.
4. Ejecuta las celdas en orden con **Shift + Enter**, o utiliza **Run All / Ejecutar todo**.

La primera celda imprime `sys.executable`: comprueba que corresponda al mismo `python.exe` seleccionado para el proyecto. El kernel del cuaderno y el intérprete del editor pueden seleccionarse por separado. [Documentación de Jupyter en VS Code](https://code.visualstudio.com/docs/datascience/jupyter-notebooks).

El cuaderno permite revisar el diagnóstico, editar el perfil, ejecutar los agentes, leer sus conclusiones y comparar las cifras con el motor de cálculo. Guarda el perfil editado en `datos/perfil_notebook.json` y conserva el caso original. La llamada al Crew utiliza otro hilo para ser compatible con el ciclo de eventos de Jupyter.

La ejecución se realiza dentro de VS Code; no necesitas iniciar un servidor de notebooks en el navegador.

## 7. Cambiar el caso de prueba

Desde el explorador de VS Code, duplica `datos/perfil_demo.json`, llama a la copia `mi_perfil.json` y edita sus valores. Ejecuta:

```powershell
conda run --no-capture-output -n habita-mx python main.py --perfil datos/mi_perfil.json --zonas datos/zonas_demo.csv
```

Reglas de entrada:

- Los montos se expresan en pesos mexicanos. Ingresos, gastos, deudas y reserva son mensuales; evita incluir deudas o gasto adicional de vivienda dentro de otros gastos para no contarlos dos veces.
- El enganche y el ahorro para gastos iniciales son bolsas separadas.
- Tasas y pesos son fracciones: `0.105` equivale a 10.5 %. Los seis pesos deben sumar `1`.
- La descripción libre aporta contexto. Las cifras estructuradas determinan cálculos y restricciones.
- Los indicadores territoriales van de 0 a 100, con sentido favorable. En `riesgos`, 100 significa menor exposición. Un campo vacío representa un dato ausente.
- El catálogo registra `simulado`, `fuente`, `fecha` y `nivel_geografico`. Este prototipo no incluye conectores a fuentes oficiales.

### Cambiar el modelo o el tiempo de espera

Si todavía no tienes un archivo `.env`, duplica `.env.example` y renombra la copia como `.env`. Su configuración inicial es:

```dotenv
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:latest
OLLAMA_TIMEOUT=240
OLLAMA_NUM_CTX=8192
```

Para cambiar el modelo, usa el nombre exacto de `ollama list` y un modelo local que admita herramientas. La demostración se verificó con `llama3.2:latest`; un modelo diferente requiere comprobar de nuevo sus respuestas. Tras editar `.env`, inicia una corrida nueva; en Jupyter, reinicia el kernel antes de ejecutar las celdas.

## 8. Pruebas y cálculo sin IA

Ejecuta las pruebas desde la terminal integrada:

```powershell
conda run --no-capture-output -n habita-mx python -m pytest -q --basetemp tmp/pruebas
```

La verificación original aprobó **25 pruebas**, que cubren amortización, tasa cero, contado, datos inválidos, restricciones, ausencia de alternativas y validación del ranking.

Para obtener únicamente la línea base de cálculo:

```powershell
conda run --no-capture-output -n habita-mx python main.py --modo calculo
```

Este modo funciona sin Ollama y se identifica como `calculo`. El modo `crew` ejecuta los cuatro agentes. El cuaderno compara los resultados oficiales de ambos modos mediante una aserción.


## Arquitectura y política de decisión

| Agente | Herramienta | Contexto recibido |
|---|---|---|
| Perfil del Usuario | `consultar_perfil` | Datos del usuario. |
| Evaluación de Zona | `evaluar_catalogo` | Perfil validado. |
| Financiero | `calcular_financiamiento` | Perfil validado. |
| Coordinador | `integrar_evaluaciones` | Perfil, Zona y Financiero. |

`Process.sequential` ejecuta las tareas en orden. Todos los agentes tienen `allow_delegation=False`; colaboran mediante `Task.context` y evidencia compartida.

Python calcula capacidad mensual, amortización y puntuaciones; los agentes utilizan las herramientas e interpretan los resultados. El control de salida exige usar la herramienta y comprueba identificadores y orden del ranking. Las cifras oficiales proceden de Python; las explicaciones del modelo requieren revisión humana.

Primero se aplican las restricciones de presupuesto, habitaciones, traslado, cobertura, seguridad, riesgos, enganche y capacidad de pago. Después se ordenan las alternativas viables mediante seis dimensiones ponderadas. Los empates se resuelven por menor pago mensual y luego por ID.

Los supuestos financieros son didácticos. El escenario de estrés compara una tasa dos puntos porcentuales mayor al contratar; no representa un cambio automático en una hipoteca fija vigente. El prototipo no calcula un CAT completo ni determina aprobación de crédito.

## Estructura del proyecto

| Ruta | Contenido |
|---|---|
| `main.py` | Entrada de terminal y diagnóstico. |
| `habita/modelos.py` | Validación de entradas y conclusiones. |
| `habita/motor.py` | Cálculos financieros, restricciones y ranking. |
| `habita/equipo.py` | Agentes, herramientas, tareas y Crew. |
| `habita/aplicacion.py` | Conexión con Ollama y exportación de resultados. |
| `Habita_MX.ipynb` | Cuaderno para ejecutar desde VS Code. |
| `datos/` | Perfil y catálogo de demostración. |
| `tests/` | Pruebas automatizadas. |
| `docs/` | Documento técnico editable y generadores. |
| `evidencia/` | Demostración y cuaderno ejecutado de referencia. |
| `salidas/` | Resultados de las corridas locales. |
| `output/` | PDF y paquete de entrega. |

## Referencias

- [Ambientes de Python en VS Code](https://code.visualstudio.com/docs/python/environments).
- [Cuadernos Jupyter en VS Code](https://code.visualstudio.com/docs/datascience/jupyter-notebooks).
- [Administración de ambientes de Conda](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html).
- [Agentes de CrewAI](https://docs.crewai.com/en/concepts/agents).
- [Tareas de CrewAI](https://docs.crewai.com/en/concepts/tasks).
- [Conexión con modelos y Ollama](https://docs.crewai.com/en/concepts/llms).
- [Ficha de Llama 3.2 de Meta](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct).
- [Russell y Norvig: Artificial Intelligence, A Modern Approach](https://aima.cs.berkeley.edu/).

Las referencias APA 7 y los límites del prototipo se desarrollan en el documento técnico de Fase 3.
