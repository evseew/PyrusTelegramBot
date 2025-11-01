# Руководство по интеграции с Pyrus API v4

## 🔌 Базовая информация

**Base URL:** `https://api.pyrus.com/v4/`

**Документация:** https://pyrus.com/en/help/api

**Формат данных:** JSON

**Кодировка:** UTF-8

## 🔐 Аутентификация

### Получение токена доступа

```typescript
POST /auth

// Request Body
{
  "login": "your_email@example.com",
  "security_key": "your_security_key"
}

// Response 200 OK
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

**Важно:**
- Токен действителен 1 час (3600 секунд)
- Храните токен в памяти и переиспользуйте для всех запросов
- При ошибке 401 - получите новый токен

### Использование токена

Все последующие запросы должны содержать заголовок:

```
Authorization: Bearer {access_token}
```

## 📋 Работа с формами

### Получение метаданных формы

```typescript
GET /forms/{form_id}

// Request Headers
Authorization: Bearer {access_token}

// Response 200 OK
{
  "id": 2304918,
  "name": "Возврат студентов",
  "fields": [
    {
      "id": 8,
      "name": "Преподаватель",
      "type": "catalog",
      "catalog_id": 12345
    },
    {
      "id": 64,
      "name": "УЧИТСЯ (заполняет СО)",
      "type": "checkmark"
    },
    {
      "id": 5,
      "name": "Филиал",
      "type": "catalog",
      "catalog_id": 67890
    },
    {
      "id": 7,
      "name": "Статус PE",
      "type": "multiple_choice"
    }
  ],
  "steps": [...],
  "author": {...}
}
```

**Зачем нужно:**
- Узнать структуру формы и ID полей
- Понять типы полей для правильного извлечения данных
- Получить названия полей для отладки

## 📊 КРИТИЧЕСКИ ВАЖНО: Пагинация в реестре форм

### Получение задач из реестра формы

Реестр формы - это список всех задач (записей) в форме. **Pyrus возвращает данные постранично с использованием курсорной пагинации.**

```typescript
GET /forms/{form_id}/register

// Query Parameters
?include_archived=false     // true/false - включать архивные задачи
&cursor={next_cursor}       // Курсор для следующей страницы (опционально)
&item_count=200            // Количество задач на странице (опционально, по умолчанию 200)

// Request Headers
Authorization: Bearer {access_token}

// Response 200 OK - ПЕРВАЯ СТРАНИЦА
{
  "tasks": [
    {
      "id": 12345678,
      "text": "Заголовок задачи",
      "create_date": "2025-01-15T10:30:00Z",
      "fields": [
        {
          "id": 8,
          "value": {
            "first_name": "Анастасия",
            "last_name": "Нечунаева"
          }
        },
        {
          "id": 64,
          "value": {
            "checkmark": "checked"
          }
        },
        {
          "id": 5,
          "value": {
            "values": ["Копейск"]
          }
        },
        {
          "id": 7,
          "value": {
            "choice_names": ["PE Start"]
          }
        }
      ]
    },
    // ... еще 199 задач
  ],
  "next_cursor": "MTIzNDU2Nzg5MA=="  // ⚠️ КЛЮЧЕВОЕ ПОЛЕ для пагинации
}
```

### ⚡ Алгоритм полной пагинации

```typescript
async function* getAllFormTasks(formId: number, includeArchived: boolean = false) {
  let cursor: string | null = null;
  let pageNumber = 0;
  
  while (true) {
    pageNumber++;
    console.log(`📄 Загрузка страницы ${pageNumber}...`);
    
    // Формируем параметры запроса
    const params: Record<string, string> = {
      include_archived: includeArchived.toString()
    };
    
    // Добавляем курсор, если это не первая страница
    if (cursor) {
      params.cursor = cursor;
    }
    
    // Делаем запрос
    const response = await axios.get(
      `https://api.pyrus.com/v4/forms/${formId}/register`,
      {
        headers: { Authorization: `Bearer ${accessToken}` },
        params: params,
        timeout: 60000  // 60 секунд таймаут
      }
    );
    
    const data = response.data;
    
    // Извлекаем задачи
    const tasks: Task[] = data.tasks || [];
    
    console.log(`  ✅ Получено ${tasks.length} задач`);
    
    // Возвращаем каждую задачу
    for (const task of tasks) {
      yield task;
    }
    
    // Проверяем наличие следующей страницы
    cursor = data.next_cursor;
    
    // Если курсора нет - это была последняя страница
    if (!cursor) {
      console.log(`🏁 Загрузка завершена. Всего страниц: ${pageNumber}`);
      break;
    }
    
    // Опциональная задержка между запросами (защита от rate limiting)
    await new Promise(resolve => setTimeout(resolve, 100));
  }
}
```

### 🎯 Использование пагинации

```typescript
// Подсчет всех задач
let totalCount = 0;
for await (const task of getAllFormTasks(2304918)) {
  totalCount++;
  
  // Обновляем прогресс каждые 100 задач
  if (totalCount % 100 === 0) {
    console.log(`Обработано ${totalCount} задач...`);
  }
}
console.log(`Всего задач: ${totalCount}`);

// Фильтрация и обработка
const validTasks: Task[] = [];
for await (const task of getAllFormTasks(2304918)) {
  // Применяем фильтры
  if (isValidPEStatus(task.fields, 7)) {
    validTasks.push(task);
  }
}

// Потоковая обработка больших форм
const stats = new Map<string, number>();
for await (const task of getAllFormTasks(792300)) {
  const teacher = extractTeacherName(task.fields, 142);
  stats.set(teacher, (stats.get(teacher) || 0) + 1);
  
  // Не храним все задачи в памяти!
}
```

## 🔍 КРИТИЧЕСКИЕ особенности пагинации

### ❗ Что нужно знать

1. **Курсор непрозрачен** - это закодированная строка, не пытайтесь её парсить или изменять
2. **Курсор временный** - действителен только для текущей сессии выборки
3. **Порядок гарантирован** - задачи всегда возвращаются в одном порядке
4. **Размер страницы** - по умолчанию 200 задач, может быть меньше на последней странице
5. **Пустой массив tasks** - возможен на последней странице, проверяйте `next_cursor`

### ⚠️ Типичные ошибки

```typescript
// ❌ НЕПРАВИЛЬНО - пропускаете данные
async function getFirstPage(formId: number) {
  const response = await fetch(`/forms/${formId}/register`);
  return response.data.tasks;  // Получили только первые 200!
}

// ✅ ПРАВИЛЬНО - получаете ВСЕ данные
async function getAllTasks(formId: number) {
  const allTasks: Task[] = [];
  let cursor: string | null = null;
  
  do {
    const params = cursor ? { cursor } : {};
    const response = await fetch(`/forms/${formId}/register`, { params });
    
    allTasks.push(...response.data.tasks);
    cursor = response.data.next_cursor;
    
  } while (cursor);
  
  return allTasks;
}
```

```typescript
// ❌ НЕПРАВИЛЬНО - используете offset вместо cursor
for (let offset = 0; offset < 1000; offset += 200) {
  const response = await fetch(`/forms/${formId}/register?offset=${offset}`);
  // Pyrus не поддерживает offset!
}

// ✅ ПРАВИЛЬНО - используете cursor
let cursor: string | null = null;
do {
  const params = cursor ? { cursor } : {};
  const response = await fetch(`/forms/${formId}/register`, { params });
  cursor = response.data.next_cursor;
} while (cursor);
```

## 📝 Структура полей задачи

### Типы полей и извлечение данных

```typescript
// Поле типа "catalog" (справочник сотрудников)
{
  "id": 8,
  "value": {
    "first_name": "Анастасия",
    "last_name": "Нечунаева",
    // или
    "text": "Анастасия Алексеевна Нечунаева",
    // или
    "name": "Анастасия Нечунаева"
  }
}

// Поле типа "checkmark" (галочка)
{
  "id": 64,
  "value": {
    "checkmark": "checked"  // или "unchecked"
  }
}

// Поле типа "catalog" (справочник филиалов)
{
  "id": 5,
  "value": {
    "values": ["Копейск", "ул. Коммунистическая 22"]
    // или
    "rows": [["Копейск"]],
    // или
    "text": "Копейск"
  }
}

// Поле типа "multiple_choice" (множественный выбор)
{
  "id": 7,
  "value": {
    "choice_names": ["PE Start"]
    // или
    "values": ["PE Start"],
    // или
    "choice_ids": [123]
  }
}

// Поле может быть вложенным (внутри секции)
{
  "id": 100,
  "value": {
    "fields": [
      {
        "id": 8,
        "value": {...}
      }
    ]
  }
}
```

### Универсальная функция извлечения значения

```typescript
function getFieldValue(fields: FormField[], fieldId: number): any {
  for (const field of fields || []) {
    // Прямое совпадение
    if (field.id === fieldId) {
      return field.value;
    }
    
    // Рекурсивный поиск в вложенных полях
    const value = field.value;
    if (value && typeof value === 'object' && Array.isArray(value.fields)) {
      const nested = getFieldValue(value.fields, fieldId);
      if (nested !== null) {
        return nested;
      }
    }
  }
  
  return null;
}
```

### Извлечение имени преподавателя

```typescript
function extractTeacherName(fields: FormField[], fieldId: number): string {
  const value = getFieldValue(fields, fieldId);
  
  if (!value) {
    return "Неизвестный преподаватель";
  }
  
  // Если это объект person
  if (typeof value === 'object') {
    // Вариант 1: first_name + last_name
    const firstName = value.first_name || '';
    const lastName = value.last_name || '';
    if (firstName || lastName) {
      return `${firstName} ${lastName}`.trim();
    }
    
    // Вариант 2: готовое поле text/name/value
    for (const key of ['text', 'name', 'value']) {
      if (typeof value[key] === 'string' && value[key].trim()) {
        return value[key].trim();
      }
    }
  }
  
  // Если это просто строка
  if (typeof value === 'string') {
    return value.trim();
  }
  
  return "Неизвестный преподаватель";
}
```

### Проверка статуса PE

```typescript
function isValidPEStatus(fields: FormField[], fieldId: number): boolean {
  const value = getFieldValue(fields, fieldId);
  const validStatuses = new Set(['PE Start', 'PE Future', 'PE 5']);
  
  if (!value) return false;
  
  // Если это объект с выбором
  if (typeof value === 'object') {
    // Проверяем choice_names
    if (Array.isArray(value.choice_names) && value.choice_names.length > 0) {
      return validStatuses.has(value.choice_names[0]);
    }
    
    // Проверяем values
    if (Array.isArray(value.values) && value.values.length > 0) {
      return validStatuses.has(value.values[0]);
    }
    
    // Проверяем rows
    if (Array.isArray(value.rows) && value.rows[0]?.[0]) {
      return validStatuses.has(value.rows[0][0]);
    }
    
    // Проверяем text/name/value
    for (const key of ['text', 'name', 'value']) {
      if (typeof value[key] === 'string') {
        return validStatuses.has(value[key]);
      }
    }
  }
  
  // Если это просто строка
  if (typeof value === 'string') {
    return validStatuses.has(value);
  }
  
  return false;
}
```

### Проверка галочки "учится"

```typescript
function isStudying(fields: FormField[], fieldId: number): boolean {
  const value = getFieldValue(fields, fieldId);
  
  if (value === null || value === undefined) {
    return false;
  }
  
  // Булево значение
  if (typeof value === 'boolean') {
    return value;
  }
  
  // Объект с checkmark
  if (typeof value === 'object' && value.checkmark) {
    return value.checkmark === 'checked';
  }
  
  // Строка
  if (typeof value === 'string') {
    const normalized = value.toLowerCase();
    return ['да', 'yes', 'true', 'checked'].includes(normalized);
  }
  
  return false;
}
```

## 🚀 Полный пример интеграции

```typescript
import axios from 'axios';

class PyrusClient {
  private baseURL = 'https://api.pyrus.com/v4/';
  private accessToken: string | null = null;
  
  constructor(
    private login: string,
    private securityKey: string
  ) {}
  
  // Аутентификация
  async authenticate(): Promise<string> {
    if (this.accessToken) {
      return this.accessToken;
    }
    
    try {
      const response = await axios.post(
        `${this.baseURL}auth`,
        {
          login: this.login,
          security_key: this.securityKey
        },
        { timeout: 30000 }
      );
      
      this.accessToken = response.data.access_token;
      return this.accessToken;
    } catch (error) {
      throw new Error(`Ошибка аутентификации: ${error.message}`);
    }
  }
  
  // Получение метаданных формы
  async getFormMeta(formId: number): Promise<any> {
    const token = await this.authenticate();
    
    try {
      const response = await axios.get(
        `${this.baseURL}forms/${formId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 30000
        }
      );
      
      return response.data;
    } catch (error) {
      throw new Error(`Ошибка получения метаданных формы ${formId}: ${error.message}`);
    }
  }
  
  // Итерация по всем задачам реестра (с пагинацией)
  async *iterateRegisterTasks(
    formId: number, 
    includeArchived: boolean = false
  ): AsyncGenerator<any> {
    const token = await this.authenticate();
    let cursor: string | null = null;
    let pageNumber = 0;
    
    while (true) {
      pageNumber++;
      
      try {
        // Формируем параметры
        const params: Record<string, string> = {
          include_archived: includeArchived.toString()
        };
        
        if (cursor) {
          params.cursor = cursor;
        }
        
        // Запрос к API
        const response = await axios.get(
          `${this.baseURL}forms/${formId}/register`,
          {
            headers: { Authorization: `Bearer ${token}` },
            params: params,
            timeout: 60000
          }
        );
        
        const data = response.data;
        const tasks = data.tasks || [];
        
        // Возвращаем каждую задачу
        for (const task of tasks) {
          yield task;
        }
        
        // Проверяем наличие следующей страницы
        cursor = data.next_cursor;
        
        if (!cursor) {
          break;  // Это была последняя страница
        }
        
        // Небольшая задержка между запросами
        await new Promise(resolve => setTimeout(resolve, 100));
        
      } catch (error) {
        console.error(`Ошибка на странице ${pageNumber}:`, error.message);
        throw error;
      }
    }
  }
  
  // Получение конкретной задачи
  async getTask(taskId: number): Promise<any> {
    const token = await this.authenticate();
    
    try {
      const response = await axios.get(
        `${this.baseURL}tasks/${taskId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 30000
        }
      );
      
      return response.data;
    } catch (error) {
      throw new Error(`Ошибка получения задачи ${taskId}: ${error.message}`);
    }
  }
}

// Использование
async function main() {
  const client = new PyrusClient(
    process.env.PYRUS_LOGIN!,
    process.env.PYRUS_SECURITY_KEY!
  );
  
  console.log('🔐 Аутентификация...');
  await client.authenticate();
  console.log('✅ Успешная аутентификация');
  
  console.log('📋 Получение метаданных формы...');
  const formMeta = await client.getFormMeta(2304918);
  console.log(`📊 Форма: ${formMeta.name}`);
  
  console.log('📥 Загрузка всех задач...');
  let count = 0;
  let validCount = 0;
  
  for await (const task of client.iterateRegisterTasks(2304918)) {
    count++;
    
    // Применяем фильтры
    if (isValidPEStatus(task.fields, 7)) {
      validCount++;
      
      const teacher = extractTeacherName(task.fields, 8);
      const isStud = isStudying(task.fields, 64);
      
      console.log(`  ${count}. ${teacher} - ${isStud ? '✅ учится' : '❌ не учится'}`);
    }
    
    // Обновляем прогресс каждые 100 задач
    if (count % 100 === 0) {
      console.log(`  📊 Обработано: ${count}, валидных: ${validCount}`);
    }
  }
  
  console.log(`\n🏁 Завершено! Всего задач: ${count}, валидных: ${validCount}`);
}
```

## ⚡ Оптимизация и производительность

### Rate Limiting
- Pyrus может ограничивать количество запросов в секунду
- Добавляйте задержку 100-200ms между запросами страниц
- При ошибке 429 (Too Many Requests) - увеличьте задержку

### Таймауты
- Стандартные запросы: 30 секунд
- Запросы к реестру: 60 секунд (большие страницы)
- Retry при ошибках сети (3 попытки с экспоненциальной задержкой)

### Память
- Используйте генераторы/async generators для потоковой обработки
- НЕ загружайте все задачи в массив сразу
- Обрабатывайте и агрегируйте данные на лету

```typescript
// ❌ ПЛОХО - загружаем все в память
const allTasks = [];
for await (const task of client.iterateRegisterTasks(formId)) {
  allTasks.push(task);
}
// Для 5000 задач = ~500MB RAM

// ✅ ХОРОШО - обрабатываем потоком
const stats = new Map();
for await (const task of client.iterateRegisterTasks(formId)) {
  const key = extractKey(task);
  stats.set(key, (stats.get(key) || 0) + 1);
}
// Постоянное использование = ~50MB RAM
```

## 🔍 Отладка

### Логирование пагинации

```typescript
async *iterateWithLogging(formId: number) {
  let cursor: string | null = null;
  let pageNumber = 0;
  let totalTasks = 0;
  
  while (true) {
    pageNumber++;
    const startTime = Date.now();
    
    const response = await axios.get(`/forms/${formId}/register`, {
      params: cursor ? { cursor } : {}
    });
    
    const tasks = response.data.tasks || [];
    const duration = Date.now() - startTime;
    
    console.log(`📄 Страница ${pageNumber}:`);
    console.log(`  ⏱️  Время: ${duration}ms`);
    console.log(`  📦 Задач: ${tasks.length}`);
    console.log(`  🔗 Курсор: ${response.data.next_cursor ? 'есть' : 'нет'}`);
    
    totalTasks += tasks.length;
    
    for (const task of tasks) {
      yield task;
    }
    
    cursor = response.data.next_cursor;
    if (!cursor) {
      console.log(`\n✅ Загрузка завершена:`);
      console.log(`  📊 Всего страниц: ${pageNumber}`);
      console.log(`  📋 Всего задач: ${totalTasks}`);
      break;
    }
  }
}
```

---

**Этот документ содержит всю необходимую информацию для корректной работы с Pyrus API, особенно в части пагинации и извлечения данных из сложных структур полей.**
