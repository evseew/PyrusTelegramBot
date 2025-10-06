/**
 * API Route: /api/data/teachers
 * Получение статистики по преподавателям
 * 
 * Использование:
 * GET /api/data/teachers
 * GET /api/data/teachers?group=oldies  (только старички)
 * GET /api/data/teachers?group=trial   (только БПЗ)
 * 
 * Ответ:
 * {
 *   "teachers": [...],
 *   "oldies_groups": {...},
 *   "trial_groups": {...},
 *   "timestamp": "2025-10-03T12:00:00Z"
 * }
 */

import { NextResponse } from 'next/server';
import { cache } from '@/lib/cache';

export async function GET(request: Request) {
  try {
    console.log('📊 [API] GET /api/data/teachers');
    
    // Проверяем наличие данных в кэше
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

    // Получаем параметры запроса
    const { searchParams } = new URL(request.url);
    const group = searchParams.get('group');

    // Фильтр по группе (опционально)
    if (group === 'oldies') {
      console.log('📊 [API] Возвращаем данные oldies_groups');
      return NextResponse.json({
        groups: data.oldies_groups,
        timestamp: data.timestamp,
      });
    }

    if (group === 'trial') {
      console.log('📊 [API] Возвращаем данные trial_groups');
      return NextResponse.json({
        groups: data.trial_groups,
        timestamp: data.timestamp,
      });
    }

    // Возвращаем все данные по преподавателям
    console.log('📊 [API] Возвращаем полные данные по преподавателям');
    return NextResponse.json({
      teachers: data.teachers,
      oldies_groups: data.oldies_groups,
      trial_groups: data.trial_groups,
      timestamp: data.timestamp,
    });
  } catch (error) {
    console.error('❌ [API] Ошибка в /api/data/teachers:', error);
    return NextResponse.json(
      {
        error: 'Внутренняя ошибка сервера',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

