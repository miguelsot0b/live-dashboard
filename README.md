# Live Dashboard - Henniges Automotive

Dashboard de producción en tiempo real para monitoreo de operaciones manufactureras.

## Características

- 📊 **KPIs en tiempo real**: Producción, Performance, Scrap, Downtime
- 📈 **Visualizaciones**: Gráficas de producción vs target, scrap top 3, timeline de status
- 🔄 **Auto-refresh**: Actualización automática cada 60 segundos
- 🎨 **Status detallados**: 16 categorías con colores e iconos específicos
- 🏭 **Multi-workcenter**: Monitoreo simultáneo de múltiples centros de trabajo
- ⏰ **Gestión de turnos**: Soporte para turnos diurnos, nocturnos y tiempo extra

## Despliegue en Streamlit Cloud

1. Asegúrate de tener los archivos en Google Drive y los permisos configurados como "Cualquiera con el enlace puede ver"
2. Actualiza los IDs de archivo en `config.py` con tus propios archivos
3. Despliega desde este repositorio en [share.streamlit.io](https://share.streamlit.io)

## Configuración Local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Uso

1. Abre el sidebar (botón hamburguesa)
2. Selecciona fecha, workcenters y turno
3. Presiona "✅ Aplicar y Activar Auto-Refresh"
4. Cierra el sidebar y deja el dashboard en modo display

## Estructura de Datos

El dashboard espera 4 archivos CSV en Google Drive:
- **Production History**: Workcenter, Date, Quantity, Part, Operation
- **Scrap Logs**: Report Date, Time Scrapped, Workcenter, Department, Extended Cost
- **Workcenter Logs**: Workcenter, Date, Time, Status, Hours
- **Cost Structure**: Description (Part), Operation, Cost

## Autor

Dashboard desarrollado para Henniges Automotive Gomez Palacio
