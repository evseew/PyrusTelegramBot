/**
 * Компонент статуса синхронизации
 * Показывает прогресс и кнопку для запуска синхронизации
 */

'use client';

import { useEffect, useState } from 'react';

interface Props {
  onSync: () => void;
}

interface SyncStatusData {
  is_syncing: boolean;
  last_sync?: string;
  has_data: boolean;
  is_stale: boolean;
  progress?: {
    current_form?: number;
    current_page?: number;
    processed_tasks?: number;
  };
  error?: string;
}

export function SyncStatus({ onSync }: Props) {
  const [status, setStatus] = useState<SyncStatusData | null>(null);

  const fetchStatus = async () => {
    try {
      console.log('🔍 [DEBUG] Загрузка статуса из /api/data/status');
      const response = await fetch('/api/data/status');
      console.log('🔍 [DEBUG] Status response:', response.status, response.statusText);
      
      if (response.ok) {
        const data = await response.json();
        console.log('🔍 [DEBUG] Status data:', data);
        setStatus(data);
      } else {
        const errorText = await response.text();
        console.error('🔍 [DEBUG] Status error:', errorText);
      }
    } catch (error) {
      console.error('❌ [DEBUG] Ошибка получения статуса:', error);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000); // Обновляем каждые 3 секунды
    return () => clearInterval(interval);
  }, []);

  if (!status) {
    return null;
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Никогда';
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="flex items-center space-x-4">
      {/* Статус */}
      <div className="text-right">
        <div className="text-xs text-gray-500">
          Последнее обновление
        </div>
        <div className="text-sm font-medium text-gray-700">
          {formatDate(status.last_sync)}
        </div>
        {status.is_stale && status.has_data && (
          <div className="text-xs text-yellow-600">
            ⚠️ Данные устарели
          </div>
        )}
        {status.error && (
          <div className="text-xs text-red-600">
            ❌ {status.error}
          </div>
        )}
      </div>

      {/* Кнопка синхронизации */}
      <button
        onClick={onSync}
        disabled={status.is_syncing}
        className={`
          flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition
          ${status.is_syncing
            ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
            : 'bg-blue-600 text-white hover:bg-blue-700'}
        `}
      >
        {status.is_syncing ? (
          <>
            <svg
              className="animate-spin h-5 w-5 text-gray-600"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              ></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            <span>Синхронизация...</span>
          </>
        ) : (
          <>
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span>Обновить</span>
          </>
        )}
      </button>

      {/* Прогресс */}
      {status.is_syncing && status.progress && (
        <div className="bg-blue-50 border border-blue-200 rounded px-3 py-2 text-xs">
          <div className="text-blue-800">
            Форма: {status.progress.current_form}
          </div>
          <div className="text-blue-600">
            Страница: {status.progress.current_page}
          </div>
          {status.progress.processed_tasks && (
            <div className="text-blue-600">
              Обработано: {status.progress.processed_tasks}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


