#!/usr/bin/env python3
import os
import sys
import requests
import json
import time
import smtplib
import subprocess
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Instalando python-dotenv...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv
    load_dotenv()


class WahaMonitor:
    def __init__(self):
        # Cargar config desde .env
        self.api_key = os.getenv('WAHA_API_KEY')
        self.base_url = os.getenv('WAHA_BASE_URL', 'http://localhost:3100')
        self.session = os.getenv('WAHA_SESSION', 'default')
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        
        # Validar que tenemos API key
        if not self.api_key:
            raise ValueError("WAHA_API_KEY no está definida en .env")
        
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Configurar logging
        self.setup_logging()
    
    def setup_logging(self):
        """Configura logging a archivo y consola"""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"waha_monitor_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.DEBUG if self.debug else logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Logging iniciado: {log_file}")
    
    def check_waha_running(self):
        """Verifica si WAHA responde usando /api/sessions (alternativa a /health)"""
        try:
            response = requests.get(
                f"{self.base_url}/api/sessions", 
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            self.logger.error(f"WAHA no responde: {e}")
            return False
    
    def get_session_status(self):
        """Obtiene estado detallado de la sesión"""
        try:
            response = requests.get(
                f"{self.base_url}/api/sessions/{self.session}", 
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {"status": "NOT_FOUND"}
            else:
                return {"status": "ERROR", "http_code": response.status_code}
        except Exception as e:
            self.logger.error(f"Error obteniendo sesión: {e}")
            return {"status": "EXCEPTION", "error": str(e)}
    
    def start_session(self):
        """Intenta iniciar la sesión si está detenida"""
        payload = {
            "name": self.session,
            "config": {"webhooks": []}
        }
        try:
            response = requests.post(
                f"{self.base_url}/api/sessions/start",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            if response.status_code in [200, 201]:
                self.logger.info("Sesión iniciada correctamente")
                return True
            elif response.status_code == 422:
                self.logger.info("Sesión ya estaba iniciada")
                return True
            else:
                self.logger.error(f"Error iniciando sesión: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Excepción iniciando sesión: {e}")
            return False
    
    def send_email_alert(self, subject, body, is_critical=False):
        """Envía alerta por email usando configuración de .env"""
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        smtp_from = os.getenv('SMTP_FROM')
        smtp_to = os.getenv('SMTP_TO')
        
        # Validar configuración SMTP
        if not all([smtp_server, smtp_user, smtp_password, smtp_from, smtp_to]):
            self.logger.error("Configuración SMTP incompleta en .env")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_from
            msg['To'] = smtp_to
            msg['Subject'] = f"{'🚨' if is_critical else '⚠️'} WAHA - {subject}"
            
            # Cuerpo del mensaje con HTML básico
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2 style="color: {'#d32f2f' if is_critical else '#f57c00'};">
                        Alerta de Monitoreo WAHA
                    </h2>
                    <p><strong>Fecha:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Servidor:</strong> {self.base_url}</p>
                    <p><strong>Sesión:</strong> {self.session}</p>
                    <hr>
                    <p>{body}</p>
                    <hr>
                    <p style="color: #666; font-size: 12px;">
                        Este mensaje fue generado automáticamente por waha_monitor.py
                    </p>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            self.logger.info(f"Email enviado: {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error enviando email: {e}")
            return False
    
    def restart_system_service(self):
        """Reinicia el servicio WAHA via systemctl"""
        # Detectar nombre del servicio (común: waha, waha-docker, whatsapp-api)
        possible_services = ['waha', 'waha-docker', 'whatsapp-api', 'waha-webjs']
        
        for service in possible_services:
            try:
                result = subprocess.run(
                    ["sudo", "systemctl", "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.logger.info(f"Reiniciando servicio: {service}")
                    restart_result = subprocess.run(
                        ["sudo", "systemctl", "restart", service],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if restart_result.returncode == 0:
                        self.logger.info(f"Servicio {service} reiniciado correctamente")
                        return True
                    else:
                        self.logger.error(f"Error reiniciando {service}: {restart_result.stderr}")
                        return False
            except Exception as e:
                continue
        
        self.logger.error("No se encontró servicio WAHA activo")
        return False
    
    def test_smtp(self):
        """Método para probar configuración de email"""
        return self.send_email_alert(
            "Test de configuración", 
            "Si recibes este email, la configuración SMTP es correcta.",
            is_critical=False
        )
    
    def run_check(self):
        """Ejecuta el chequeo completo"""
        self.logger.info("=== INICIANDO CHEQUEO WAHA ===")
        
        # 1. VERIFICAR SI WAHA RESPONDE
        if not self.check_waha_running():
            self.logger.error("CRÍTICO: WAHA no responde")
            
            # Intentar reiniciar
            if self.restart_system_service():
                self.logger.info("Esperando 15 segundos después del reinicio...")
                time.sleep(15)
                
                if not self.check_waha_running():
                    msg = "WAHA fue reiniciado pero sigue sin responder. Se requiere intervención manual."
                    self.send_email_alert("Servicio CAÍDO - Reinicio fallido", msg, is_critical=True)
                    return False
            else:
                msg = "No se pudo reiniciar el servicio WAHA. Verificar servidor Debian 13."
                self.send_email_alert("Servicio CAÍDO - Reinicio imposible", msg, is_critical=True)
                return False
        
        self.logger.info("WAHA responde correctamente")
        
        # 2. VERIFICAR ESTADO DE SESIÓN
        session_data = self.get_session_status()
        
        if session_data.get("status") == "EXCEPTION":
            self.logger.error(f"Error obteniendo sesión: {session_data.get('error')}")
            return False
        
        status = session_data.get("status")
        engine = session_data.get("engine", {})
        engine_state = engine.get("state")
        numero = session_data.get("me", {}).get("id", "N/A")
        push_name = session_data.get("me", {}).get("pushName", "N/A")
        
        self.logger.info(f"Número: {numero} ({push_name})")
        self.logger.info(f"Estado sesión: {status}")
        self.logger.info(f"Estado engine: {engine_state}")
        
        # 3. EVALUAR ESTADOS
        if status == "WORKING" and engine_state == "CONNECTED":
            self.logger.info("✅ TODO OK: Sesión activa y conectada")
            return True
            
        elif status == "STOPPED":
            self.logger.warning("Sesión DETENIDA - Intentando iniciar...")
            if self.start_session():
                self.send_email_alert(
                    "Sesión reiniciada automáticamente",
                    f"La sesión '{self.session}' estaba detenida y se inició correctamente.",
                    is_critical=False
                )
            else:
                self.send_email_alert(
                    "Fallo al iniciar sesión",
                    f"No se pudo iniciar la sesión '{self.session}' automáticamente.",
                    is_critical=True
                )
            return False
            
        elif status == "SCAN_QR":
            msg = f"La sesión '{self.session}' requiere escanear código QR."
            self.logger.warning(msg)
            self.send_email_alert("Requiere escanear QR", msg, is_critical=True)
            return False
            
        elif engine_state != "CONNECTED":
            msg = f"Engine desconectado (estado: {engine_state}). Posible problema de red o bloqueo de WhatsApp."
            self.logger.warning(msg)
            self.send_email_alert("WhatsApp desconectado", msg, is_critical=True)
            return False
            
        else:
            msg = f"Estado desconocido: {status} / {engine_state}"
            self.logger.warning(msg)
            self.send_email_alert("Estado desconocido", msg, is_critical=True)
            return False


def main():
    try:
        monitor = WahaMonitor()
        
        # Si se pasa argumento "test-smtp", solo probar email
        if len(sys.argv) > 1 and sys.argv[1] == "test-smtp":
            print("Probando configuración SMTP...")
            if monitor.test_smtp():
                print("✅ Email de prueba enviado correctamente")
            else:
                print("❌ Fallo al enviar email de prueba")
            return
        
        # Ejecutar chequeo normal
        monitor.run_check()
        
    except ValueError as e:
        print(f"Error de configuración: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
