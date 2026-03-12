# 🚀 GUÍA: SUBIR PROYECTO A GITHUB

## OPCIÓN 1: Si NO tienes cuenta de GitHub (5 minutos)

### PASO 1: Crea tu cuenta
1. **Abre** https://github.com/signup
2. **Rellena:**
   - Username: algo como `tu_nombre_github`
   - Email: tu correo
   - Password: contraseña fuerte
3. **Verifica** el email
4. **Eres desarrollador?** → Elige "Yes" (es gratis)
5. **Intereses** → Marca lo que uses (web dev, machine learning, etc)

### PASO 2: Crea SSH Key (para no escribir contraseña cada vez)

En PowerShell:
```powershell
# Genera SSH key
ssh-keygen -t ed25519 -C "tu_email@gmail.com"

# Presiona ENTER 3 veces (sin escribir nada)
# Esto crea keys en: C:\Users\tu_usuario\.ssh\

# Copia la clave pública
Get-Content C:\Users\tu_usuario\.ssh\id_ed25519.pub | Set-Clipboard
```

### PASO 3: Agrega SSH Key a GitHub

1. **Abre** https://github.com/settings/keys (login primero)
2. **Click** "New SSH key"
3. **Pega** la clave que copiaste
4. **Click** "Add SSH key"

---

## OPCIÓN 2: Si YA tienes cuenta de GitHub (3 minutos)

### PASO 1: Crea repositorio en GitHub

1. **Abre** https://github.com/new
2. **Repository name:** `EnterpriseAnalytics` (o tu nombre)
3. **Description:** "Analytics platform with ML predictions and visualizations"
4. **Public** o **Private** (según quieras)
5. **NO marques** "Initialize with README" (ya tienes uno)
6. **Click** "Create repository"

### PASO 2: Configura Git localmente

En PowerShell, ve a tu carpeta del proyecto:

```powershell
cd "C:\Users\bryan\OneDrive\Desktop\Proyectos\EnterpriseAnalytics"

# Inicializa git si no existe
git init

# Configura tu nombre y email
git config user.name "Tu Nombre Completo"
git config user.email "tu_email@gmail.com"

# Verifica configuración
git config --list
```

### PASO 3: Agrega los archivos

```powershell
# Agrega todos los archivos
git add .

# Verifica qué se va a subir
git status

# (Opcional) Crea archivo .gitignore para excluir archivos grandes
```

Crea `.gitignore` en la raíz del proyecto con:

```
# Python
__pycache__/
*.py[cod]
*$py.class
venv/
env/
.venv/

# Node
node_modules/
.npm

# Docker
.DS_Store
*.log

# IDE
.vscode/
.idea/
*.swp

# Datos sensibles
.env
.env.local
secrets.json

# Datos grandes
*.pyc
build/
dist/
*.egg-info/

# Base de datos
*.db
*.sqlite3
pgdata/
redisdata/

# Caché
.pytest_cache/
.coverage
htmlcov/
```

### PASO 4: Primer commit

```powershell
git add .gitignore
git commit -m "Initial commit: Enterprise Analytics platform with ML predictions"
```

### PASO 5: Conecta con GitHub

**Opción A: SSH (recomendado)**
```powershell
# Reemplaza "tu_usuario" y "EnterpriseAnalytics"
git remote add origin git@github.com:tu_usuario/EnterpriseAnalytics.git

# Verifica
git remote -v
```

**Opción B: HTTPS (más fácil si no quieres SSH)**
```powershell
git remote add origin https://github.com/tu_usuario/EnterpriseAnalytics.git

# Verifica
git remote -v
```

### PASO 6: Sube el código

```powershell
# Renombra rama a "main" (si está en "master")
git branch -M main

# Sube todo
git push -u origin main

# De ahora en adelante:
git push
```

---

## ✅ VERIFICACIÓN

Después de PUSH, abre: https://github.com/tu_usuario/EnterpriseAnalytics

Deberías ver:
- ✅ Todos tus archivos
- ✅ README.md como presentación
- ✅ Carpetas: backend/, frontend/, etc
- ✅ Historial de commits

---

## 🔄 FLUJO DE TRABAJO DIARIO

Una vez configured, el flujo es simple:

```powershell
# 1. Haz cambios en los archivos
# 2. Ver cambios
git status

# 3. Agregar cambios
git add .

# 4. Commit (guarda versión)
git commit -m "Descripción de qué cambió"

# 5. Sube a GitHub
git push
```

**Ejemplos de mensajes de commit:**

```
git commit -m "Fix: arreglar predicciones con datos reales"
git commit -m "Feature: agregar búsqueda en dashboard"
git commit -m "Docs: actualizar guía de predicciones"
git commit -m "Refactor: mejorar estructura de carpetas"
git commit -m "Bug fix: corregir error en visualizaciones"
```

---

## 🛡️ PROTEGE DATOS SENSIBLES

**IMPORTANTE:** No subes a GitHub:

```
❌ .env files (credenciales)
❌ Contraseñas
❌ API keys
❌ Base de datos pgdata/
❌ node_modules/ (es ENORME)
❌ __pycache__/
```

El `.gitignore` cuida de muchos, pero revisa:

```powershell
# Ver qué va a subir ANTES de push
git diff --cached

# Si subiste algo sensible POR ERROR:
git rm --cached archivo_sensible.env
git commit -m "Remove sensitive file"
git push
```

---

## 🤝 COLABORAR CON OTROS

Si quieres que otro desarrollador trabaje contigo:

### Opción A: Developer access
1. **Settings → Collaborators**
2. **Add people**
3. Invite por email/username

### Opción B: Forks (para públicos)
1. Otros hacen "Fork" de tu repo
2. Hacen cambios en su copia
3. Hacen "Pull Request"
4. Tú revisas y aceptas/rechazas

---

## 📊 OPCIONES RECOMENDADAS PARA TU REPO

Como es proyecto PRIVADO de empresa:

```
✅ Private repository
✅ Add these as collaborators:
   - Team members
✅ Proteger branch "main"
   - Settings → Branches
   - Require pull request reviews
```

---

## 🆘 PROBLEMAS COMUNES

### "fatal: not a git repository"
```powershell
git init
```

### "Permission denied (publickey)"
```powershell
# Re-agregar SSH key
ssh-add C:\Users\tu_usuario\.ssh\id_ed25519

# O usar HTTPS en lugar de SSH
git remote set-url origin https://github.com/tu_usuario/EnterpriseAnalytics.git
```

### "rejected ... master/main"
```powershell
# Tienes commits en GitHub que no tienes localmente
git pull origin main
# Luego:
git push
```

### Accidentalmente subiste archivo grande
```powershell
# Borralo del historio (peligroso, úsalo con cuidado)
git filter-branch --tree-filter 'rm -f archivo_grande.csv' HEAD
git push --force
```

---

## 📈 BADGES Y EXTRAS

Una vez en GitHub, puedes agregar a tu README:

```markdown
# EnterpriseAnalytics

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95-green)
![React](https://img.shields.io/badge/React-Next.js%2014-blue)
![License](https://img.shields.io/badge/License-MIT-green)

[Ver código en GitHub](https://github.com/tu_usuario/EnterpriseAnalytics)
```

---

## 🎯 ESTRUCTURA QUE VERÁS EN GITHUB

```
EnterpriseAnalytics/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── core/
│   ├── models/
│   ├── routers/
│   └── services/
├── frontend/
│   ├── package.json
│   ├── src/
│   ├── public/
│   └── next.config.ts
├── docker-compose.yml
├── .gitignore
├── README.md
└── [otros archivos]
```

---

## ✨ COMANDOS CLAVE RESUMEN

```powershell
# Setup inicial
git init
git config user.name "Nombre"
git remote add origin https://github.com/user/repo.git

# Trabajo diario
git add .
git commit -m "descripción"
git push

# Ver historial
git log --oneline

# Ramas
git branch nombre_rama
git checkout nombre_rama
git push -u origin nombre_rama

# Actualizar código remoto
git pull
```

---

## 🎓 PRÓXIMOS PASOS (Intermedios)

Una vez hayas dominado lo básico:

1. **Branches** - Crear ramas para nuevas features
2. **Pull Requests** - Revisar código antes de fusionar
3. **GitHub Actions** - CI/CD automático
4. **Issues** - Tracking de bugs y features
5. **Projects** - Kanban board para organizar trabajo

Pero por ahora, con `git add . → git commit → git push` es suficiente.

---

## 💡 CONSEJO FINAL

```
No esperes al "proyecto perfecto" para subir.
Sube AHORA, comienza a registrar versiones.

Las mejores prácticas vienen después.
Lo importante es empezar. 🚀
```
