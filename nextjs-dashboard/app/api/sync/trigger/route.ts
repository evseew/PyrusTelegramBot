/**
 * API Route: /api/sync/trigger
 * Запуск фоновой синхронизации данных из Pyrus
 * 
 * Использование:
 * POST /api/sync/trigger
 * 
 * Ответ:
 * { "success": true, "message": "Синхронизация запущена" }
 */

import { NextResponse } from 'next/server';
import { PyrusClient } from '@/lib/pyrus-client';
import { PyrusDataAnalyzer } from '@/lib/analyzer';
import { cache } from '@/lib/cache';

/**
 * Фоновая задача синхронизации
 * Не блокирует HTTP-ответ
 */
async function runBackgroundSync() {
  try {
    console.log('🚀 [SYNC] Запуск фоновой синхронизации...');

    // Обновляем статус
    cache.setSyncStatus({
      is_syncing: true,
      progress: {
        current_form: 0,
        current_page: 0,
        total_tasks: 0,
        processed_tasks: 0,
      },
    });

    // Инициализация клиента
    const client = new PyrusClient(
      process.env.PYRUS_LOGIN!,
      process.env.PYRUS_SECURITY_KEY!,
      process.env.PYRUS_API_URL
    );

    const analyzer = new PyrusDataAnalyzer(client);

    // Запускаем анализ с отслеживанием прогресса
    const result = await analyzer.runFullAnalysis((stage, page, tasksCount) => {
      const currentForm = stage === 'form_2304918' ? 2304918 : 792300;
      
      cache.setSyncStatus({
        is_syncing: true,
        progress: {
          current_form: currentForm,
          current_page: page,
          processed_tasks: tasksCount,
        },
      });

      console.log(`📄 [SYNC] ${stage}: страница ${page}, задач ${tasksCount}`);
    });

    // Сохраняем результат в кэш
    cache.setAnalysisResult(result);

    // Обновляем статус
    cache.setSyncStatus({
      is_syncing: false,
      last_sync: new Date().toISOString(),
    });

    console.log('✅ [SYNC] Фоновая синхронизация завершена успешно');
  } catch (error) {
    console.error('❌ [SYNC] Ошибка синхронизации:', error);

    cache.setSyncStatus({
      is_syncing: false,
      error: error instanceof Error ? error.message : 'Неизвестная ошибка',
    });
  }
}

export async function POST() {
  try {
    console.log('🔄 [API] POST /api/sync/trigger');
    
    // Проверяем переменные окружения
    if (!process.env.PYRUS_LOGIN || !process.env.PYRUS_SECURITY_KEY) {
      console.error('❌ [API] Отсутствуют переменные окружения');
      return NextResponse.json(
        {
          error: 'Не настроены переменные окружения PYRUS_LOGIN и PYRUS_SECURITY_KEY',
        },
        { status: 500 }
      );
    }

    // Проверяем, не идет ли уже синхронизация
    const status = cache.getSyncStatus();
    if (status.is_syncing) {
      console.warn('⚠️ [API] Синхронизация уже выполняется');
      return NextResponse.json(
        {
          error: 'Синхронизация уже выполняется',
          progress: status.progress,
        },
        { status: 409 }
      );
    }

    // Запускаем синхронизацию в фоне (не блокируем ответ)
    runBackgroundSync().catch((error) => {
      console.error('💥 [API] Критическая ошибка фоновой синхронизации:', error);
    });

    // Сразу возвращаем успешный ответ
    console.log('✅ [API] Синхронизация запущена в фоновом режиме');
    return NextResponse.json(
      {
        success: true,
        message: 'Синхронизация запущена в фоновом режиме',
      },
      { status: 202 }
    );
  } catch (error) {
    console.error('❌ [API] Ошибка в /api/sync/trigger:', error);
    return NextResponse.json(
      {
        error: 'Внутренняя ошибка сервера',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

