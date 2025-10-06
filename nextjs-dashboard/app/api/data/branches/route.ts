/**
 * API Route: /api/data/branches
 * Получение статистики по филиалам
 * 
 * Использование:
 * GET /api/data/branches
 * 
 * Ответ:
 * {
 *   "branches": [
 *     {
 *       "name": "Копейск",
 *       "form_2304918_total": 150,
 *       "form_2304918_studying": 120,
 *       "return_percentage": 80,
 *       ...
 *     }
 *   ],
 *   "timestamp": "2025-10-03T12:00:00Z"
 * }
 */

import { NextResponse } from 'next/server';
import { cache } from '@/lib/cache';

export async function GET() {
  try {
    console.log('🏢 [API] GET /api/data/branches');
    
    // Получаем данные из кэша
    const data = cache.getAnalysisResult();

    if (!data) {
      console.warn('⚠️ [API] Данные не найдены в кэше');
      return NextResponse.json(
        {
          error: 'Данные не найдены. Запустите синхронизацию через POST /api/sync/trigger',
        },
        { status: 404 }
      );
    }

    // Возвращаем статистику по филиалам
    console.log('🏢 [API] Возвращаем данные по филиалам:', data.branches.length);
    return NextResponse.json({
      branches: data.branches,
      timestamp: data.timestamp,
    });
  } catch (error) {
    console.error('❌ [API] Ошибка в /api/data/branches:', error);
    return NextResponse.json(
      {
        error: 'Внутренняя ошибка сервера',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

