#!/bin/bash
# =============================================================
# setup.sh — Script de instalación completa del proyecto
# Ubuntu Server 24.04 LTS en Oracle VirtualBox
# =============================================================
set -e

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
echo -e "${CYAN}════════════════════════════════════════${NC}"
echo -e "${CYAN}  RESILIENCIA — Setup Automático        ${NC}"
echo -e "${CYAN}════════════════════════════════════════${NC}"

# ── 1. Dependencias del sistema ──────────────────────────────
echo -e "\n${YELLOW}[1/6] Instalando dependencias...${NC}"
sudo apt-get update -qq
sudo apt-get install -y -qq \
    docker.io docker-compose-v2 \
    curl git ufw \
    postgresql-client-common postgresql-client-15

# Agregar usuario al grupo docker
sudo usermod -aG docker "$USER"

# ── 2. Habilitar y arrancar Docker ───────────────────────────
echo -e "\n${YELLOW}[2/6] Configurando Docker...${NC}"
sudo systemctl enable docker --now

# ── 3. Configurar Firewall (UFW) ─────────────────────────────
echo -e "\n${YELLOW}[3/6] Configurando Firewall...${NC}"
sudo ufw --force enable
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 8080/tcp   # Passbolt HTTP
sudo ufw allow 8443/tcp   # Passbolt HTTPS
sudo ufw allow 5000/tcp   # CheckMK
sudo ufw allow 3000/tcp   # Dashboard UI
sudo ufw allow 3001/tcp   # Dashboard API
sudo ufw allow 5432/tcp   # PostgreSQL (restringir a IP necesaria en prod)

# ── 4. Crear estructura de directorios ───────────────────────
echo -e "\n${YELLOW}[4/6] Creando directorios...${NC}"
mkdir -p ~/resiliencia/{logs,backups,init}

# ── 5. Copiar archivos .env ──────────────────────────────────
echo -e "\n${YELLOW}[5/6] Configurando variables de entorno...${NC}"
if [ ! -f ~/resiliencia/.env ]; then
    cp servidor/.env.example ~/resiliencia/.env
    echo -e "${YELLOW}⚠  Edita ~/resiliencia/.env con tus datos reales antes de continuar${NC}"
    echo "   Especialmente: DB_MIRROR_HOST, SMTP_USER, SMTP_PASS, ADMIN_EMAIL"
fi

# ── 6. Levantar contenedores ─────────────────────────────────
echo -e "\n${YELLOW}[6/6] Levantando contenedores...${NC}"
cd ~/resiliencia
cp ~/proyecto-resiliencia/servidor/docker-compose.yml .
cp -r ~/proyecto-resiliencia/servidor/backup-agent .
cp -r ~/proyecto-resiliencia/servidor/failover-agent .
cp -r ~/proyecto-resiliencia/servidor/dashboard .

docker compose --env-file .env up -d --build

echo -e "\n${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✓ Instalación completa                ${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "  Dashboard:  ${CYAN}http://$(hostname -I | awk '{print $1}'):3000${NC}"
echo -e "  Passbolt:   ${CYAN}http://$(hostname -I | awk '{print $1}'):8080${NC}"
echo -e "  CheckMK:    ${CYAN}http://$(hostname -I | awk '{print $1}'):5000${NC}"
echo ""
echo -e "  Logs:       ${YELLOW}docker compose logs -f${NC}"
echo -e "  Detener:    ${YELLOW}docker compose down${NC}"
echo ""
