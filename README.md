# WAHA Monitor

Sistema de monitoreo automático para WAHA (WhatsApp API) en Debian 13. Detecta caídas del servicio, desconexiones de sesión y reinicia automáticamente cuando es posible.

## Características

- ✅ Verificación de disponibilidad del servicio WAHA
- ✅ Detección de estados de sesión (WORKING, STOPPED, SCAN_QR, etc.)
- ✅ Reinicio automático de sesiones detenidas
- ✅ Reinicio del servicio systemd si WAHA no responde
- ✅ Alertas por email en caso de fallos críticos
- ✅ Logging detallado a archivo y consola
- ✅ Configuración mediante variables de entorno (.env)

## Requisitos

- Python 3.8+
- Debian 12/13 (o compatible)
- WAHA instalado y configurado con API key
- Acceso sudo para reiniciar servicios (opcional, para auto-restart)

## Instalación

### 1. Clonar o crear el directorio

```bash
mkdir -p ~/waha-monitor && cd ~/waha-monitor
```

```bash
python3 -m venv venv
source venv/bin/activate
```

```bash
pip install python-dotenv requests
```

```bash
touch .env
```

```bash
# WAHA Configuration
WAHA_API_KEY=tu_api_key_de_waha
WAHA_BASE_URL=http://localhost:3100
WAHA_SESSION=default

# SMTP Configuration (ejemplo Gmail)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tucorreo@gmail.com
SMTP_PASSWORD=tu_app_password_de_gmail
SMTP_FROM=tucorreo@gmail.com
SMTP_TO=destinatario@email.com

# Opcional
DEBUG=false
```

```bash
mkdir -p logs
```

```bash
source venv/bin/activate
python waha_monitor.py
```

```bash
python waha_monitor.py test-smtp
```

```bash
crontab -e
```

```bash
*/5 * * * * cd /home/tu-usuario/waha-monitor && /home/tu-usuario/waha-monitor/venv/bin/python waha_monitor.py >> /home/tu-usuario/waha-monitor/logs/cron.log 2>&1
```

```bash
sudo visudo
```

```bash
tu-usuario ALL=(ALL) NOPASSWD: /bin/systemctl restart waha, /bin/systemctl restart waha-docker, /bin/systemctl restart whatsapp-api
```

| Método | Endpoint                  | Descripción                                                     |
| ------ | ------------------------- | --------------------------------------------------------------- |
| GET    | `/api/sessions`           | Listar todas las sesiones (usado como health check alternativo) |
| GET    | `/api/sessions/{session}` | Obtener estado detallado de la sesión                           |
| POST   | `/api/sessions/start`     | Iniciar sesión si está detenida                                 |


| Estado                  | Significado                   | Acción del script                   |
| ----------------------- | ----------------------------- | ----------------------------------- |
| `WORKING` + `CONNECTED` | ✅ Todo funciona correctamente | Ninguna                             |
| `STOPPED`               | Sesión detenida               | Iniciar sesión vía API              |
| `SCAN_QR`               | Esperando escaneo de QR       | Enviar alerta por email             |
| `DISCONNECTED`          | Desconectado de WhatsApp      | Enviar alerta por email             |
| HTTP error / timeout    | WAHA no responde              | Reiniciar servicio systemd + alerta |

```bash
~/waha-monitor/
├── .env                    # Configuración (no versionar)
├── waha_monitor.py         # Script principal
├── venv/                   # Entorno virtual
├── logs/
│   ├── waha_monitor_YYYYMMDD.log   # Logs diarios
│   └── cron.log                      # Output de cron
└── README.md               # Este archivo
```

| Variable        | Descripción                      | Default                 |
| --------------- | -------------------------------- | ----------------------- |
| `WAHA_API_KEY`  | Clave API de WAHA (obligatoria)  | -                       |
| `WAHA_BASE_URL` | URL base de WAHA                 | `http://localhost:3100` |
| `WAHA_SESSION`  | Nombre de la sesión a monitorear | `default`               |
| `SMTP_SERVER`   | Servidor SMTP para alertas       | -                       |
| `SMTP_PORT`     | Puerto SMTP                      | `587`                   |
| `SMTP_USER`     | Usuario SMTP                     | -                       |
| `SMTP_PASSWORD` | Contraseña SMTP                  | -                       |
| `SMTP_FROM`     | Remitente de emails              | -                       |
| `SMTP_TO`       | Destinatario de alertas          | -                       |
| `DEBUG`         | Modo debug (más logs)            | `false`                 |


```bash
sudo systemctl list-units --type=service | grep -i waha
```

```bash
curl -H "X-Api-Key: TU_API_KEY" http://localhost:3100/api/sessions
```

```bash
sudo -l
```
