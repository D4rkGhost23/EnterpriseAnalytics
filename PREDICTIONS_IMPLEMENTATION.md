# 🎯 PLAN DE IMPLEMENTACIÓN: PREDICCIONES

## 📊 Estado Actual

### Backend (✅ Casi completo)
**Ubicación:** `backend/routers/predictions.py` + `backend/services/prediction_engine.py`

**Modelos ML disponibles:**
1. **Linear Regression** - Pronósticos de ventas con bandas de confianza
2. **Random Forest** - Predicciones con importancia de características
3. **Decision Trees** - Extracción de reglas empresariales
4. **K-Means** - Segmentación de clientes
5. **Isolation Forest** - Detección de anomalías

**Herramientas usadas:**
- `scikit-learn` - Modelos ML
- `pandas` / `numpy` - Procesamiento de datos
- FastAPI - API REST
- SQLAlchemy - Base de datos de jobs

**Endpoints disponibles:**
- `POST /api/v1/predictions/` - Ejecutar predicción
- `GET /api/v1/predictions/jobs/{job_id}` - Obtener estado

### Frontend (✅ 95% implementado)
**Ubicación:** `frontend/src/app/dashboard/predictions/page.tsx`

**Features:**
- ✅ Selector de dataset y modelo
- ✅ Configuración de parámetros (clusters, períodos, etc)
- ✅ Botón "Run Prediction"
- ✅ Polling de estado del trabajo
- ✅ Visualización de métricas
- ✅ Importancia de características
- ✅ Reglas de decisión
- ✅ Detección de anomalías

## 🔧 Qué Falta/Arreglar

### 1. **Backend - Función `_rebuild_dataframe`** (CRÍTICA)
```python
# Línea 21 - FALTA IMPLEMENTACIÓN
async def _rebuild_dataframe(dataset: Dataset) -> pd.DataFrame:
    raise NotImplementedError(...)
```

**Problema:** El backend genera datos sintéticos en lugar de usar los datos reales del CSV

**Solución:** Implementar lectura de archivo CSV del dataset

---

### 2. **Backend - Deserialización del schema** (CRÍTICA)
```python
# Línea 61
schema = dataset.schema_json  # ← Puede ser string JSON
```

**Problema:** El schema puede estar como string JSON, no dict

**Solución:** Agregar `json.loads()` si es necesario

---

### 3. **Frontend - Visualización de resultados** (IMPORTANTE)
Los resultados de predicción no se visualizan como gráficos interactivos

**Solución:** Integrar ChartFactory para mostrar:
- Pronósticos con bandas de confianza (líneas)
- Importancia de features (barras)
- Clusters (scatter plot)
- Anomalías (puntos destacados)

---

## 🚀 Plan de Acción (Orden de Prioridad)

### PASO 1: Arreglar Backend (30 minutos)
✅ Implementar lectura real de datos del CSV
✅ Parsear schema JSON correctamente
✅ Generar respuesta con formato correcto

### PASO 2: Conectar Frontend con Visualizaciones (20 minutos)
✅ Renderizar gráficos de resultados con ChartFactory
✅ Mostrar tabla de anomalías
✅ Mejorar UI de resultados

### PASO 3: Pruebas y Validación (15 minutos)
✅ Ejecutar predicción con CSV real
✅ Verificar cada tipo de modelo
✅ Validar output en frontend

---

## 📦 Dependencias (Ya Instaladas)

```python
# requirements.txt ya contiene:
scikit-learn==1.5.1        # Modelos ML
pandas==2.2.0              # Datos
numpy==1.26.4              # Matrices
joblib==1.4.2              # Serialización
```

---

## 🎨 Herramientas Recomendadas

### Para mejorar predicciones:
- **XGBoost** - Mejor que Random Forest (opcional)
- **LightGBM** - Muchísimo más rápido (opcional)
- **SHAP** - Explicabilidad (opcional)

### Para visualizaciones:
- **Recharts** - ✅ Ya instalado en frontend
- **Apache ECharts** - Alternativa (opcional)

---

## 📈 Casos de Uso por Modelo

**Linear Regression (Pronóstico de Ventas)**
```
Entrada: Dataset con fecha y cantidad
Salida: 
  - Pronóstico para próximos 12-24 meses
  - Bandas de confianza (95%)
  - R² score
```

**Random Forest (Performance Prediction)**
```
Entrada: Features numéricas y target
Salida:
  - Top 5 características más importantes
  - Predicción para nuevos registros
  - Precisión (accuracy/MAE/RMSE)
```

**Decision Tree (Rule Extraction)**
```
Entrada: Features categóricas y numéricas
Salida:
  - Árbol de decisión en texto
  - Reglas "IF-THEN" legibles
  - Importancia de variables
```

**K-Means (Segmentación)**
```
Entrada: Features de clientes
Salida:
  - N clusters (2-8)
  - Inércia y Silhuette score
  - Centros de clusters
```

**Isolation Forest (Anomalías)**
```
Entrada: Cualquier dataset
Salida:
  - Índices de anomalías (1/-1)
  - % de anomalías detectadas
  - Score de anomalía por registro
```

---

## 💾 Estructura de Respuesta Esperada

```json
{
  "job_id": 123,
  "status": "completed",
  "result": {
    "model_type": "linear_regression",
    "metrics": {
      "r2_score": 0.85,
      "mae": 1234.5,
      "rmse": 1567.8
    },
    "feature_importances": {
      "feature1": 0.45,
      "feature2": 0.35,
      "feature3": 0.20
    },
    "viz_metadata": {
      "type": "forecast_chart",
      "title": "Revenue Forecast",
      "data": [...],
      "forecast": [...],
      "confidence_band": {...}
    },
    "rules": null,
    "anomaly_count": 0
  }
}
```

---

## ✨ Mejoras Opcionales

### A Corto Plazo:
1. Agregar validación de datos entrada
2. Mejorar manejo de valores faltantes
3. Escalamiento automático de features
4. Soporte para múltiples targets

### A Mediano Plazo:
1. Guardar modelos entrenados (joblib)
2. Predecir con modelos guardados
3. Versionado de modelos
4. A/B testing de modelos

### A Largo Plazo:
1. AutoML (selección automática de modelo)
2. Ensemble de modelos
3. Deep Learning (LSTM para series temporales)
4. Predicciones en tiempo real (streaming)

---

## 🧪 Testing Rápido

Una vez implementado, prueba con este CSV:

```
date,sales,region
2024-01-01,1000,North
2024-01-02,1200,North
2024-01-03,950,South
...
```

Luego:
1. Sube el CSV a Datasets
2. Ve a Predictions
3. Selecciona "Sales Forecast"
4. Ajusta "Forecast Periods" a 12
5. Haz clic "Run"
6. Espera resultado y verifica gráfico

---

## 📞 Comandos Útiles

```bash
# Ver logs del backend
docker-compose logs backend -f

# Ver estado de job específico
curl http://localhost:8000/api/v1/predictions/jobs/1 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Ejecutar test de predicciones
docker-compose exec backend pytest tests/test_prediction_engine.py -v
```
