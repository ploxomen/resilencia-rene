# RESILIENCIA — Sistema de Alta Disponibilidad con Docker
### Proyecto Universitario · Infraestructura y Redes

---

## Descripción General

Sistema dockerizado de alta disponibilidad que integra **Passbolt**, **CheckMK** y una
base de datos PostgreSQL principal, con replicación incremental cada 2 minutos hacia una
**DB Espejo en la nube** y failover automático.

---

## Arquitectura

```
┌──────────────────────────────────────────┐          ┌──────────────────┐
│  SERVIDOR (Ubuntu 24.04 en VirtualBox)   │          │  NUBE            │
│                                          │          │                  │
│  ┌──────────┐   ┌──────────┐            │  sync    │  ┌────────────┐  │
│  │ PASSBOLT │   │ CHECKMK  │            │ ──────►  │  │ DB ESPEJO  │  │
│  │  :8080   │   │  :5000   │            │          │  │  :5433     │  │
│  └────┬─────┘   └────┬─────┘            │          │  └────────────┘  │
│       │              │                   │          └──────────────────┘
│       └──────┬────────┘                  │
│         ┌────▼──────────┐                │
│         │  DB PRINCIPAL  │               │
│         │  PostgreSQL    │               │
│         │  :5432         │               │
│         └───────────────┘               │
│                                          │
│  ┌──────────────┐  ┌────────────────┐   │
│  │ backup-agent │  │ failover-agent │   │
│  │  cada 2 min  │  │  cada 15 seg   │   │
│  └──────────────┘  └────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │  DASHBOARD  :3000                │   │
│  │  Estado · Backups · Logs         │   │
│  └──────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

---

## Requisitos Previos

| Software      | Versión mínima |
|--------------|----------------|
| Ubuntu Server | 24.04 LTS      |
| Docker        | 24.x           |
| Docker Compose| v2             |
| RAM           | 4 GB           |
| Disco         | 20 GB          |

---

## Estructura del Proyecto

```
proyecto-resiliencia/
├── servidor/
│   ├── docker-compose.yml       # Orquestación principal
│   ├── .env.example             # Variables de entorno (copiar a .env)
│   ├── backup-agent/
│   │   ├── backup.py            # Lógica de backups incrementales
│   │   └── Dockerfile
│   ├── failover-agent/
│   │   ├── failover.py          # Monitoreo y failover automático
│   │   └── Dockerfile
│   └── dashboard/
│       ├── server.js            # API + WebSocket backend
│       ├── package.json
│       ├── Dockerfile
│       └── public/
│           └── index.html       # Dashboard UI
├── nube/
│   ├── docker-compose.yml       # DB Espejo en VPS
│   └── pg_hba_custom.conf       # Acceso remoto a PostgreSQL
└── scripts/
    └── setup.sh                 # Instalación automática
```

---

## Instalación Paso a Paso

### Paso 1 — Preparar el servidor (Ubuntu en VirtualBox)

```bash
# Clonar el proyecto
git clone <repo> ~/proyecto-resiliencia
cd ~/proyecto-resiliencia

# Ejecutar setup automático
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### Paso 2 — Configurar variables de entorno

```bash
cp servidor/.env.example ~/resiliencia/.env
nano ~/resiliencia/.env
```

Editar obligatoriamente:
- `DB_MIRROR_HOST` → IP pública de tu VPS/nube
- `SMTP_USER` / `SMTP_PASS` → cuenta Gmail con App Password
- `ADMIN_EMAIL` → correo del administrador

### Paso 3 — Preparar la DB Espejo en la nube

En tu VPS (AWS, DigitalOcean, Azure, etc.):

```bash
# Copiar los archivos de nube/
scp -r nube/ usuario@IP_VPS:~/db-espejo/
ssh usuario@IP_VPS
cd ~/db-espejo

# Crear .env para la nube
cat > .env << EOF
DB_MIRROR_USER=mirror_admin
DB_MIRROR_PASSWORD=Yy1"pI15}+6[
DB_NAME=resiliencia_db
EOF

docker compose --env-file .env up -d
```

Abrir puerto en el firewall del VPS:
```bash
sudo ufw allow 5433/tcp
```

### Paso 4 — Levantar el sistema principal

```bash
cd ~/resiliencia
docker compose --env-file .env up -d --build
```

### Paso 5 — Verificar

```bash
# Ver todos los contenedores
docker compose ps

# Ver logs en tiempo real
docker compose logs -f failover-agent backup-agent

# Acceder al dashboard
# http://IP_SERVIDOR:3000
```

---

## Pruebas de Resiliencia

### Prueba 1: Notificación al apagar un servicio

```bash
# Simular caída de Passbolt
docker stop passbolt
# → El dashboard muestra el contenedor en rojo
# → Log registra el evento con timestamp

# Restaurar
docker start passbolt
```

### Prueba 2: Failover automático a DB Espejo

```bash
# Simular caída de DB principal
docker stop db-principal

# El failover-agent detecta la caída en ≤15 segundos
# → Envía correo al administrador
# → El dashboard cambia el banner a "DB ESPEJO"
# → Passbolt y CheckMK se reconectan

# Restaurar la DB principal
docker start db-principal
# → Reconexión automática ≤15 segundos
```

### Prueba 3: Verificar backups

```bash
# Ver archivos de backup generados
ls -lh ~/resiliencia/backups/

# Ver el log del backup-agent
tail -f ~/resiliencia/logs/backup.log
```

---

## Dashboard

Acceder en: **http://IP_SERVIDOR:3000**

| Sección           | Descripción |
|-------------------|-------------|
| Barra superior    | DB actualmente en uso (verde=principal, rojo=espejo) |
| Cards de contenedores | Estado UP/DOWN de cada contenedor |
| Topología         | Diagrama SVG animado del sistema |
| Backups           | Historial con timestamp, tamaño y tiempo de envío |
| Log de eventos    | Todos los eventos con tipo y timestamp |

---

## Variables de Entorno

| Variable | Descripción |
|----------|-------------|
| `DB_USER` | Usuario de PostgreSQL principal |
| `DB_PASSWORD` | Contraseña de la DB principal |
| `DB_NAME` | Nombre de la base de datos |
| `DB_MIRROR_HOST` | IP/hostname de la DB espejo en la nube |
| `DB_MIRROR_PORT` | Puerto de la DB espejo (default: 5433) |
| `DB_MIRROR_USER` | Usuario de la DB espejo |
| `DB_MIRROR_PASSWORD` | Contraseña de la DB espejo |
| `SMTP_HOST` | Servidor SMTP para notificaciones |
| `SMTP_PORT` | Puerto SMTP (default: 587) |
| `SMTP_USER` | Usuario SMTP |
| `SMTP_PASS` | Contraseña SMTP (App Password en Gmail) |
| `ADMIN_EMAIL` | Correo del administrador para alertas |
| `CMK_PASSWORD` | Contraseña de CheckMK |

---

## Tecnologías Utilizadas

| Componente | Tecnología |
|------------|------------|
| Contenedores | Docker + Docker Compose v2 |
| Gestor de contraseñas | Passbolt CE |
| Monitoreo de red | CheckMK Raw 2.3 |
| Base de datos | PostgreSQL 15 |
| Backup incremental | pg_dump + Python 3.11 |
| Failover agent | Python + psycopg2 + Docker SDK |
| Dashboard API | Node.js 20 + Express + Socket.IO |
| Dashboard UI | HTML5 + CSS3 + JavaScript (Vanilla) |
| SO | Ubuntu Server 24.04 LTS |
| Virtualización | Oracle VirtualBox |

---

## Autores

Proyecto universitario — Infraestructura y Redes  
Sistema de Alta Disponibilidad con Docker y Replicación de Base de Datos
