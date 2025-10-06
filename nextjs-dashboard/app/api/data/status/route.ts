/**
 * API Route: /api/data/status
 * Получение статуса синхронизации
 * 
 * Использование:
 * GET /api/data/status
 * 
 * Ответ:
 * {
 *   "is_syncing": false,
 *   "last_sync": "2025-10-03T12:00:00Z",
 *   "has_data": true,
 *   "is_stale": false,
 *   "progress": {...}
 * }
 */

import { NextResponse } from 'next/server';
import { cache } from '@/lib/cache';

export async function GET() {
  try {
    console.log('📡 [API] GET /api/data/status');
    
    const status = cache.getSyncStatus();
    const hasData = cache.hasData();
    const isStale = cache.isStale(15); // 15 минут
    const lastUpdate = cache.getLastUpdate();

    const responseData = {
      is_syncing: status.is_syncing,
      last_sync: status.last_sync || lastUpdate,
      has_data: hasData,
      is_stale: isStale,
      progress: status.progress,
      error: status.error,
    };

    console.log('📡 [API] Статус:', responseData);
    
    return NextResponse.json(responseData);
  } catch (error) {
    console.error('❌ [API] Ошибка в /api/data/status:', error);
    return NextResponse.json(
      {
        error: 'Внутренняя ошибка сервера',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

