# La Casa al Dia

Aplicacion web full stack basada en el documento de gerencia de proyectos. Usa Django, SQLite y una SPA React servida por Django.

## Modulos incluidos

- Autenticacion y registro por roles: Cliente, Oficios Varios, Lavanderia y Administrador.
- Perfiles editables, datos de ubicacion, estado de aprobacion y servicios/precios del prestador.
- Reservas con agenda, modalidad domicilio/punto fisico, estados, pago demo y calificacion.
- Ofertas creadas por clientes, postulaciones de prestadores y seleccion del trabajador.
- Notificaciones internas, mensajeria, historial de pagos, sanciones, disputas y panel de metricas.
- Persistencia en SQLite para que los registros queden guardados.
- Exportacion CSV desde el panel administrativo.

## Instalacion local

Desde esta carpeta:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py seed_lcd
python manage.py runserver
```

Abrir: http://127.0.0.1:8000/

Usuarios demo:

- Administrador: `admin@lcd.com` / `admin123`
- Cliente: `cliente@lcd.com` / `cliente123`
- Oficios varios: `oficios@lcd.com` / `oficios123`
- Lavanderia: `lavanderia@lcd.com` / `lav123`

## Despliegue recomendado

1. Cambiar `SECRET_KEY`, poner `DEBUG = False` y configurar `ALLOWED_HOSTS` en `lcd_project/settings.py`.
2. Usar PostgreSQL o MySQL en produccion si se espera alto trafico.
3. Ejecutar `python manage.py collectstatic`.
4. Servir Django con Gunicorn/uWSGI y un proxy como Nginx.
5. Configurar HTTPS, backups de base de datos y variables de entorno.
6. Reemplazar el pago demo por credenciales reales de PayU u otra pasarela.

Para una entrega academica/local, SQLite y `runserver` son suficientes para demostrar funcionalidad completa.
