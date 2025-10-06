# Техническое задание: Next.js плагин для генерации отчетов Pyrus

## 🎯 Цель проекта

Создать веб-плагин на Next.js, который воспроизводит функциональность Python-скрипта `final_fixed_report.py` для анализа данных из Pyrus API и генерации Excel отчетов с группировкой преподавателей по эффективности.

## 📋 Общий план реализации

### 1️⃣ Инфраструктура и настройка (Этап 1)
- Инициализация Next.js проекта с TypeScript
- Настройка переменных окружения для Pyrus API
- Создание базовой архитектуры проекта
- Установка необходимых зависимостей

### 2️⃣ API клиент и типизация (Этап 2)
- Создание Pyrus API клиента
- Определение TypeScript интерфейсов для данных
- Реализация аутентификации и получения токена
- Функции для работы с формами и задачами

### 3️⃣ Бизнес-логика анализа (Этап 3)
- Извлечение и валидация данных из полей форм
- Фильтрация по статусам PE (PE Start, PE Future, PE 5)
- Группировка по преподавателям и филиалам
- Применение правил исключений

### 4️⃣ Генерация Excel отчетов (Этап 4)
- Создание структуры Excel файлов с несколькими вкладками
- Применение стилей и форматирования
- Группировка преподавателей по категориям
- Присвоение призов по рейтингу

### 5️⃣ Веб-интерфейс (Этап 5)
- Создание UI для загрузки конфигурации
- Отображение прогресса обработки
- Возможность скачивания готовых отчетов

## 🏗️ Архитектура проекта

```
nextjs-pyrus-plugin/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── api/               # API routes
│   │   │   ├── auth/          # Аутентификация Pyrus
│   │   │   ├── forms/         # Работа с формами
│   │   │   └── reports/       # Генерация отчетов
│   │   ├── components/        # React компоненты
│   │   ├── globals.css        # Стили
│   │   ├── layout.tsx         # Главный layout
│   │   └── page.tsx          # Главная страница
│   ├── lib/                   # Утилиты и библиотеки
│   │   ├── pyrus-client.ts    # Pyrus API клиент
│   │   ├── data-analyzer.ts   # Анализ данных
│   │   ├── excel-generator.ts # Генерация Excel
│   │   └── types.ts          # TypeScript типы
│   ├── config/               # Конфигурация
│   │   ├── form-fields.ts    # Настройки полей форм
│   │   └── exclusions.ts     # Исключения преподавателей
│   └── utils/               # Вспомогательные функции
├── public/                  # Статические файлы
├── .env.local              # Переменные окружения
├── package.json
└── README.md
```

## 🔧 Технический стек

### Frontend
- **Next.js 14** с App Router
- **TypeScript** для типизации
- **Tailwind CSS** для стилизации
- **React Hook Form** для форм
- **Zustand** для состояния приложения

### Backend/API
- **Next.js API Routes** для серверной логики
- **Axios** для HTTP запросов к Pyrus API
- **ExcelJS** для генерации Excel файлов
- **Zod** для валидации данных

### Утилиты
- **date-fns** для работы с датами
- **lodash** для манипуляций с данными
- **file-saver** для скачивания файлов

## 📝 Детальная спецификация компонентов

### 1. Pyrus API клиент (`lib/pyrus-client.ts`)

```typescript
interface PyrusClient {
  // Аутентификация
  authenticate(): Promise<string>;
  
  // Получение метаданных формы
  getFormMeta(formId: number): Promise<FormMeta>;
  
  // Итерация по задачам реестра
  iterateRegisterTasks(formId: number, includeArchived?: boolean): AsyncGenerator<Task>;
  
  // Получение конкретной задачи
  getTask(taskId: number): Promise<Task>;
}
```

### 2. Анализатор данных (`lib/data-analyzer.ts`)

```typescript
interface DataAnalyzer {
  // Анализ формы 2304918 (возврат студентов)
  analyzeForm2304918(): Promise<TeacherStats[]>;
  
  // Анализ формы 792300 (конверсия после БПЗ)
  analyzeForm792300(): Promise<TeacherStats[]>;
  
  // Объединение статистики
  mergeTeacherStats(): Promise<CombinedStats>;
  
  // Подготовка данных по филиалам
  prepareBranchData(): Promise<BranchStats[]>;
}
```

### 3. Генератор Excel (`lib/excel-generator.ts`)

```typescript
interface ExcelGenerator {
  // Создание полного отчета
  createFullReport(data: AnalysisData): Promise<Buffer>;
  
  // Создание вкладки "Вывод старичков"
  createOldiesSheet(workbook: Workbook, data: TeacherStats[]): void;
  
  // Создание вкладки "Конверсия после БПЗ"
  createTrialSheet(workbook: Workbook, data: TeacherStats[]): void;
  
  // Создание вкладки статистики филиалов
  createBranchSummarySheet(workbook: Workbook, data: BranchStats[]): void;
  
  // Создание детальных вкладок по филиалам
  createBranchDetailSheets(workbook: Workbook, data: BranchData): void;
}
```

## 🎨 Пользовательский интерфейс

### Главная страница
```typescript
// Основные элементы UI:
- Форма настройки подключения к Pyrus API
- Загрузка файла исключений преподавателей (JSON)
- Кнопка "Создать отчет"
- Индикатор прогресса обработки
- Область для скачивания готового Excel файла
- Логи выполнения операций
```

### Компоненты
1. **ConfigForm** - форма настройки API подключения
2. **ProgressIndicator** - индикатор прогресса
3. **FileUpload** - загрузка файлов конфигурации
4. **ReportDownload** - скачивание готовых отчетов
5. **LogViewer** - просмотр логов выполнения

## 🔍 Детальная логика обработки данных

### Извлечение данных из полей форм

```typescript
// Функции извлечения значений из сложных структур Pyrus
function extractFieldValue(fields: FormField[], fieldId: number): any;
function extractTeacherName(fields: FormField[], fieldId: number): string;
function extractBranchName(fields: FormField[], fieldId: number): string;
function isValidPEStatus(fields: FormField[], fieldId: number): boolean;
function isStudying(fields: FormField[], fieldId: number): boolean;
```

### Конфигурация полей форм

```typescript
// config/form-fields.ts
export const FORM_CONFIGS = {
  2304918: {
    name: "Возврат студентов (старички)",
    fields: {
      teacher: 8,      // Поле с преподавателем
      studying: 64,    // Поле "УЧИТСЯ (заполняет СО)"
      branch: 5,       // Поле с филиалом
      status: 7        // Поле со статусом PE
    }
  },
  792300: {
    name: "Конверсия после БПЗ (новый клиент)",
    fields: {
      teacher: 142,    // Поле с преподавателем
      studying: 187,   // Поле "учится"
      branch: 226,     // Поле с филиалом
      status: 228      // Поле со статусом PE
    }
  }
};
```

### Правила группировки и призы

```typescript
// Группировка преподавателей по количеству студентов
export const TEACHER_GROUPS = {
  oldies: {
    "35+": { prizes: ["iPad", "HonorPad", "HonorPad", "HonorPad"], count: 4 },
    "16-34": { prize: "HonorPad", count: 3 },
    "6-15": { prize: "Подписка в Tg Premium", count: 3 }
  },
  trial: {
    "16+": { prizes: ["iPad", "HonorPad", "HonorPad", "HonorPad"], count: 4 },
    "11-15": { prize: "HonorPad", count: 3 },
    "5-10": { prize: "Подписка в Tg Premium", count: 3 }
  }
};

// Призы для филиалов (топ-5)
export const BRANCH_PRIZES = [
  "Interactive Display",
  "Кофемachine + 2 кг кофе",
  "Кофемachine",
  "20 000 руб.",
  "10 000 руб."
];
```

## 📊 Структуры данных (TypeScript интерфейсы)

```typescript
interface TeacherStats {
  name: string;
  form2304918: {
    total: number;
    studying: number;
    percentage: number;
    data: TaskData[];
  };
  form792300: {
    total: number;
    studying: number;
    percentage: number;
    data: TaskData[];
  };
  totalPercentage: number;
}

interface BranchStats {
  name: string;
  form2304918: { total: number; studying: number; percentage: number };
  form792300: { total: number; studying: number; percentage: number };
  totalPercentage: number;
  isExcludedFromCompetition: boolean;
}

interface TaskData {
  taskId: number;
  teacher: string;
  branch: string;
  isStudying: boolean;
  timestamp: string;
}

interface FormField {
  id: number;
  value: any;
  fields?: FormField[];
}

interface Task {
  id: number;
  fields: FormField[];
  [key: string]: any;
}

interface ExclusionConfig {
  oldies: string[];
  trial: string[];
}
```

## 🔐 Переменные окружения

```bash
# .env.local
PYRUS_API_URL=https://api.pyrus.com/v4/
PYRUS_LOGIN=your_login
PYRUS_SECURITY_KEY=your_security_key

# Опционально для продакшена
NODE_ENV=production
NEXT_PUBLIC_APP_URL=https://your-domain.com
```

## 📦 Зависимости (package.json)

```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "typescript": "^5.0.0",
    "@types/react": "^18.0.0",
    "@types/node": "^20.0.0",
    
    "axios": "^1.6.0",
    "exceljs": "^4.4.0",
    "file-saver": "^2.0.5",
    "react-hook-form": "^7.48.0",
    "zustand": "^4.4.0",
    "zod": "^3.22.0",
    
    "tailwindcss": "^3.3.0",
    "date-fns": "^2.30.0",
    "lodash": "^4.17.21",
    "@types/lodash": "^4.14.0",
    "@types/file-saver": "^2.0.0"
  },
  "devDependencies": {
    "@types/react-dom": "^18.0.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "eslint": "^8.0.0",
    "eslint-config-next": "^14.0.0"
  }
}
```

## 🚀 Пошаговый план реализации

### Шаг 1: Инициализация проекта (10 мин)
```bash
npx create-next-app@latest pyrus-report-plugin --typescript --tailwind --app
cd pyrus-report-plugin
npm install axios exceljs file-saver react-hook-form zustand zod date-fns lodash
npm install -D @types/lodash @types/file-saver
```

### Шаг 2: Создание базовой структуры (15 мин)
- Создать папки `lib/`, `config/`, `utils/`
- Настроить `types.ts` с основными интерфейсами
- Создать файл `.env.local` с переменными окружения

### Шаг 3: Pyrus API клиент (30 мин)
- Реализовать `PyrusClient` класс
- Добавить методы аутентификации
- Создать функции для работы с формами и задачами
- Протестировать подключение к API

### Шаг 4: Анализатор данных (45 мин)
- Создать `DataAnalyzer` класс
- Реализовать извлечение данных из полей форм
- Добавить фильтрацию по статусам PE
- Создать группировку по преподавателям и филиалам

### Шаг 5: Генератор Excel (60 мин)
- Создать `ExcelGenerator` класс
- Реализовать создание вкладок с данными
- Добавить стилизацию и форматирование
- Создать систему присвоения призов

### Шаг 6: API Routes (20 мин)
- Создать `/api/auth` для аутентификации
- Создать `/api/reports/generate` для генерации отчетов
- Добавить обработку ошибок и валидацию

### Шаг 7: UI компоненты (40 мин)
- Создать форму настройки подключения
- Добавить индикатор прогресса
- Создать компонент загрузки файлов
- Реализовать скачивание отчетов

### Шаг 8: Интеграция и тестирование (30 мин)
- Соединить все компоненты
- Протестировать полный цикл создания отчета
- Добавить обработку ошибок
- Оптимизировать производительность

## ⚡ Ключевые особенности реализации

### Асинхронная обработка
```typescript
// Используем Server-Sent Events для отслеживания прогресса
export async function* generateReportWithProgress(config: ReportConfig) {
  yield { step: 'auth', progress: 10 };
  await authenticate();
  
  yield { step: 'analyzing_2304918', progress: 30 };
  const oldiesData = await analyzeForm2304918();
  
  yield { step: 'analyzing_792300', progress: 60 };
  const trialData = await analyzeForm792300();
  
  yield { step: 'generating_excel', progress: 90 };
  const excelBuffer = await generateExcel(combinedData);
  
  yield { step: 'complete', progress: 100, result: excelBuffer };
}
```

### Обработка больших объемов данных
```typescript
// Используем стриминг для обработки больших форм
async function* processFormData(formId: number) {
  const batchSize = 100;
  let batch: Task[] = [];
  
  for await (const task of client.iterateRegisterTasks(formId)) {
    batch.push(task);
    
    if (batch.length >= batchSize) {
      yield processBatch(batch);
      batch = [];
    }
  }
  
  if (batch.length > 0) {
    yield processBatch(batch);
  }
}
```

### Кэширование и оптимизация
```typescript
// Кэшируем токены аутентификации и метаданные форм
const authCache = new Map<string, { token: string; expires: number }>();
const formMetaCache = new Map<number, FormMeta>();

// Используем мемоизацию для тяжелых вычислений
const memoizedAnalyzeTeacher = useMemo(() => 
  analyzeTeacherData, [teacherData]
);
```

## 🎯 Критерии готовности

### Функциональность
- ✅ Подключение к Pyrus API работает
- ✅ Данные извлекаются из обеих форм (2304918, 792300)
- ✅ Применяются фильтры по статусам PE
- ✅ Исключения преподавателей работают корректно
- ✅ Группировка и призы назначаются правильно
- ✅ Excel файл генерируется со всеми вкладками
- ✅ Стили и форматирование применяются

### Производительность
- ✅ Обработка 1000+ задач за разумное время
- ✅ Прогресс-бар показывает актуальное состояние
- ✅ Нет блокировки UI во время обработки
- ✅ Память используется эффективно

### Удобство использования
- ✅ Интуитивный интерфейс
- ✅ Понятные сообщения об ошибках
- ✅ Возможность загрузки собственных исключений
- ✅ Быстрое скачивание готовых отчетов

## 🔧 Конфигурация для разных проектов

Для адаптации под другие проекты создайте файл конфигурации:

```typescript
// config/project-config.ts
export interface ProjectConfig {
  forms: {
    [formId: number]: {
      name: string;
      fields: {
        teacher: number;
        studying: number;
        branch: number;
        status: number;
      };
      validStatuses: string[];
      exclusionType: 'oldies' | 'trial';
    };
  };
  grouping: {
    [category: string]: {
      [range: string]: {
        prize?: string;
        prizes?: string[];
        count: number;
      };
    };
  };
  branchExclusions: string[];
  branchPrizes: string[];
}
```

## 📚 Документация для ИИ

При создании этого плагина ИИ должен:

1. **Точно воспроизвести логику** извлечения данных из сложных структур Pyrus
2. **Сохранить алгоритмы** группировки и присвоения призов
3. **Реализовать идентичное** форматирование Excel файлов
4. **Обеспечить масштабируемость** для обработки больших объемов данных
5. **Создать гибкую конфигурацию** для адаптации под разные проекты

### Особое внимание к:
- Рекурсивному поиску значений в вложенных полях форм
- Правильной нормализации названий филиалов
- Точному применению исключений преподавателей
- Корректной сортировке и группировке результатов
- Идентичному стилю Excel таблиц с эмодзи и цветами

---

**Этот документ содержит всю необходимую информацию для создания полнофункционального Next.js плагина, который точно воспроизведет поведение оригинального Python скрипта.**
