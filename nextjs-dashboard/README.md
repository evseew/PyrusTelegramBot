# 📊 Pyrus Dashboard - Next.js

Веб-дашборд для анализа данных из Pyrus API. Отображает статистику по преподавателям и филиалам в интерактивном формате (аналог Excel-отчетов из `final_fixed_report.py`).

---

## 🎯 Возможности

✅ **Полная пагинация Pyrus API** - корректная обработка больших форм (5000+ задач)  
✅ **Фоновая синхронизация** - данные загружаются в фоне, не блокируя UI  
✅ **In-Memory кэш** - быстрые ответы после первой загрузки  
✅ **3 вкладки статистики**:
  - 👴 Вывод старичков (форма 2304918)
  - 👶 Конверсия после БПЗ (форма 792300)
  - 🏢 Статистика по филиалам

✅ **Группировка преподавателей** с призами (iPad, HonorPad, Tg Premium)  
✅ **Автообновление** каждые 30 секунд  
✅ **Красивый UI** на Tailwind CSS

---

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
cd nextjs-dashboard
npm install
```

### 2. Настройка переменных окружения

Создайте файл `.env.local` в корне `nextjs-dashboard/`:

```env
PYRUS_LOGIN=your_email@example.com
PYRUS_SECURITY_KEY=your_security_key_here
PYRUS_API_URL=https://api.pyrus.com/v4/
```

> **Важно:** Скопируйте credentials из вашего `.env` файла проекта PyrusTelegramBot

### 3. Запуск в режиме разработки

```bash
npm run dev
```

Откройте [http://localhost:3000](http://localhost:3000)

### 4. Первая синхронизация

После открытия дашборда:
1. Нажмите кнопку **"Обновить"** в правом верхнем углу
2. Дождитесь завершения синхронизации (2-5 минут для больших форм)
3. Данные автоматически отобразятся

---

## 📂 Структура проекта

```
nextjs-dashboard/
├── lib/                          # Бизнес-логика
│   ├── types.ts                  # TypeScript типы
│   ├── pyrus-client.ts           # Клиент Pyrus API с пагинацией
│   ├── analyzer.ts               # Анализ данных (аналог Python)
│   ├── cache.ts                  # Кэш-менеджер
│   └── helpers.ts                # Вспомогательные функции
│
├── api/                          # Next.js API Routes
│   ├── sync/
│   │   └── trigger.ts            # POST /api/sync/trigger - запуск синхронизации
│   └── data/
│       ├── status.ts             # GET /api/data/status - статус синхронизации
│       ├── teachers.ts           # GET /api/data/teachers - данные преподавателей
│       └── branches.ts           # GET /api/data/branches - данные филиалов
│
├── components/                   # React компоненты
│   ├── Dashboard.tsx             # Главный компонент дашборда
│   ├── TeachersTable.tsx         # Таблица преподавателей
│   ├── BranchesTable.tsx         # Таблица филиалов
│   └── SyncStatus.tsx            # Статус синхронизации
│
├── app/                          # Next.js 13+ App Router
│   ├── page.tsx                  # Главная страница
│   ├── layout.tsx                # Root layout
│   └── globals.css               # Глобальные стили
│
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── README.md
```

---

## 🔧 API Endpoints

### 1. Запуск синхронизации

```bash
POST /api/sync/trigger
```

**Ответ:**
```json
{
  "success": true,
  "message": "Синхронизация запущена в фоновом режиме"
}
```

### 2. Статус синхронизации

```bash
GET /api/data/status
```

**Ответ:**
```json
{
  "is_syncing": false,
  "last_sync": "2025-10-03T12:00:00Z",
  "has_data": true,
  "is_stale": false,
  "progress": {
    "current_form": 2304918,
    "current_page": 15,
    "processed_tasks": 300
  }
}
```

### 3. Данные преподавателей

```bash
GET /api/data/teachers
GET /api/data/teachers?group=oldies  # Только старички
GET /api/data/teachers?group=trial   # Только БПЗ
```

### 4. Данные филиалов

```bash
GET /api/data/branches
```

---

## 🎨 Как работает пагинация

### Проблема
Pyrus API возвращает данные постранично (по 200 задач). Для форм с 5000+ задачами нужно сделать 25+ запросов с правильной обработкой `next_cursor`.

### Решение

**Файл:** `lib/pyrus-client.ts`

```typescript
async *iterateRegisterTasks(formId: number) {
  let cursor: string | null = null;
  
  while (true) {
    // Запрос с курсором
    const params = cursor ? { cursor } : {};
    const response = await fetch(`/forms/${formId}/register`, { params });
    
    const data = response.data;
    const tasks = data.tasks || [];
    
    // Возвращаем каждую задачу через generator
    for (const task of tasks) {
      yield task;  // ⚡ Потоковая обработка
    }
    
    // Проверяем наличие следующей страницы
    cursor = data.next_cursor;
    if (!cursor) break;  // Последняя страница
    
    await new Promise(r => setTimeout(r, 100));  // Rate limiting
  }
}
```

### Использование

```typescript
let count = 0;
for await (const task of client.iterateRegisterTasks(2304918)) {
  count++;
  // Обрабатываем задачу БЕЗ загрузки всех в память
}
```

---

## 🔄 Как работает фоновая синхронизация

### Схема

```
Пользователь → POST /api/sync/trigger
                      ↓
                Запуск фоновой задачи (не блокирует ответ)
                      ↓
                Ответ 202: "Синхронизация запущена"
                      
Фоновая задача:
  1. Обновление статуса (is_syncing: true)
  2. Инициализация PyrusClient
  3. Анализ формы 2304918 (пагинация)
  4. Анализ формы 792300 (пагинация)
  5. Вычисление процентов
  6. Группировка преподавателей
  7. Сохранение в кэш
  8. Обновление статуса (is_syncing: false)

Фронтенд:
  - Опрашивает GET /api/data/status каждые 3 секунды
  - Отображает прогресс
  - После завершения загружает данные
```

---

## 📊 Сравнение с Excel-отчетом

| Excel вкладка | Компонент | API Endpoint |
|---------------|-----------|--------------|
| Вывод старичков | `TeachersTable` (type=oldies) | `/api/data/teachers?group=oldies` |
| Конверсия после БПЗ | `TeachersTable` (type=trial) | `/api/data/teachers?group=trial` |
| Статистика по филиалам | `BranchesTable` | `/api/data/branches` |
| Детальные вкладки по филиалам | *(планируется)* | - |

---

## 🐛 Отладка

### Логи в консоли сервера

```bash
npm run dev

# В консоли увидите:
🚀 Запуск фоновой синхронизации...
📊 Анализ формы 2304918 (старички)...
  📄 form_2304918: страница 1, задач 200
  📄 form_2304918: страница 2, задач 200
  ...
✅ Форма 2304918: всего 500, отфильтровано 450, исключено 10
📊 Анализ формы 792300 (новый клиент)...
✅ Анализ завершен за 45.23 секунд
✅ Результат анализа сохранен в кэш
```

### Проверка данных через API

```bash
# Статус
curl http://localhost:3000/api/data/status

# Преподаватели
curl http://localhost:3000/api/data/teachers | jq '.teachers | length'

# Филиалы
curl http://localhost:3000/api/data/branches | jq '.branches[0]'
```

---

## 🚢 Деплой на production

### 1. Vercel (рекомендуется)

```bash
# Установите Vercel CLI
npm i -g vercel

# Деплой
cd nextjs-dashboard
vercel

# Настройте Environment Variables в Vercel Dashboard:
# PYRUS_LOGIN, PYRUS_SECURITY_KEY, PYRUS_API_URL
```

### 2. Docker

```dockerfile
# Dockerfile (создайте в nextjs-dashboard/)
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
```

```bash
docker build -t pyrus-dashboard .
docker run -p 3000:3000 \
  -e PYRUS_LOGIN=your_email \
  -e PYRUS_SECURITY_KEY=your_key \
  pyrus-dashboard
```

### 3. VPS (Ubuntu)

```bash
# На сервере
git clone <your-repo>
cd nextjs-dashboard
npm install
npm run build

# PM2 для production
npm install -g pm2
pm2 start npm --name "pyrus-dashboard" -- start
pm2 save
pm2 startup
```

---

## 🔐 Безопасность

⚠️ **Важно:**
- Никогда не коммитьте `.env.local` в git
- Используйте переменные окружения для credentials
- Добавьте аутентификацию для production (NextAuth.js)
- Ограничьте доступ к API Routes через middleware

---

## 📈 Оптимизация для больших форм

### Текущие настройки

- **Таймаут запроса:** 60 секунд
- **Rate limiting:** 100ms задержка между страницами
- **Кэш:** In-memory (данные сбрасываются при перезапуске)

### Для production

1. **Добавьте Redis** для персистентного кэша
2. **Настройте cron** для автоматической синхронизации
3. **Используйте webhooks Pyrus** для обновления в реальном времени
4. **Добавьте индикатор прогресса** с процентами

---

## 🆘 Частые проблемы

### "Данные не найдены"
**Решение:** Нажмите кнопку "Обновить" для запуска синхронизации

### "Синхронизация уже выполняется"
**Решение:** Дождитесь завершения текущей синхронизации (2-5 минут)

### Ошибка аутентификации Pyrus
**Решение:** Проверьте `PYRUS_LOGIN` и `PYRUS_SECURITY_KEY` в `.env.local`

### Таймаут при загрузке больших форм
**Решение:** Увеличьте таймаут в `pyrus-client.ts` (строка 98)

---

## 🔮 Roadmap

- [ ] Экспорт в Excel (аналог Python скрипта)
- [ ] Детальные страницы по филиалам
- [ ] Фильтрация по датам
- [ ] Графики и диаграммы (Chart.js)
- [ ] Аутентификация (NextAuth.js)
- [ ] WebSocket для real-time обновлений
- [ ] Redis кэш для production
- [ ] Мобильная версия

---

## 📝 Лицензия

MIT

---

## 🤝 Поддержка

По вопросам создайте Issue в репозитории или свяжитесь с разработчиком.

---

**Создано как альтернатива Python-скрипту `final_fixed_report.py`** 🚀

