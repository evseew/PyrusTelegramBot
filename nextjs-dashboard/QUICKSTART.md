# ⚡ Быстрый старт за 3 минуты

## 1️⃣ Установка (1 минута)

```bash
cd nextjs-dashboard
npm install
```

## 2️⃣ Настройка credentials (30 секунд)

Создайте файл `.env.local`:

```bash
cat > .env.local << EOF
PYRUS_LOGIN=$(grep PYRUS_LOGIN ../.env | cut -d '=' -f2)
PYRUS_SECURITY_KEY=$(grep PYRUS_SECURITY_KEY ../.env | cut -d '=' -f2)
PYRUS_API_URL=https://api.pyrus.com/v4/
EOF
```

> **Вручную:** Скопируйте `PYRUS_LOGIN` и `PYRUS_SECURITY_KEY` из вашего `.env`

## 3️⃣ Запуск (30 секунд)

```bash
npm run dev
```

Откройте: **http://localhost:3000**

## 4️⃣ Первая синхронизация (2-5 минут)

1. Нажмите кнопку **"Обновить"** (правый верхний угол)
2. Дождитесь завершения загрузки
3. Готово! Данные отобразятся автоматически

---

## 📊 Что увидите

- **Вкладка "Вывод старичков"** - таблицы по группам (35+, 16-34, 6-15) с призами
- **Вкладка "Конверсия после БПЗ"** - таблицы по группам (16+, 11-15, 5-10)
- **Вкладка "Статистика по филиалам"** - топ-5 филиалов с призами

---

## 🔧 Проблемы?

### Ошибка "PYRUS_LOGIN не установлен"
→ Проверьте `.env.local` - должны быть `PYRUS_LOGIN` и `PYRUS_SECURITY_KEY`

### "Cannot find module 'next'"
→ Запустите `npm install`

### Пустой экран / белая страница
→ Откройте консоль браузера (F12) и проверьте ошибки

---

## 🚀 Production деплой

**Vercel (1 клик):**
```bash
npm i -g vercel
vercel
```

**Docker:**
```bash
docker build -t pyrus-dashboard .
docker run -p 3000:3000 -e PYRUS_LOGIN=... -e PYRUS_SECURITY_KEY=... pyrus-dashboard
```

---

**Полная документация:** [README.md](./README.md)

