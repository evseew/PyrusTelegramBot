/**
 * Главный компонент дашборда
 * Отображает статистику по преподавателям и филиалам
 */

'use client';

import { useEffect, useState } from 'react';
import { TeachersTable } from './TeachersTable';
import { BranchesTable } from './BranchesTable';
import { SyncStatus } from './SyncStatus';
import type { AnalysisResult } from '../lib/types';

export function Dashboard() {
  const [data, setData] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'oldies' | 'trial' | 'branches'>('oldies');

  // Загрузка данных
  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      console.log('🔍 [DEBUG] Загрузка данных из /api/data/teachers');
      const response = await fetch('/api/data/teachers');
      
      console.log('🔍 [DEBUG] Response status:', response.status);
      console.log('🔍 [DEBUG] Response statusText:', response.statusText);
      console.log('🔍 [DEBUG] Response headers:', Object.fromEntries(response.headers.entries()));
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('🔍 [DEBUG] Response error body:', errorText);
        throw new Error(`Данные не найдены (${response.status}): ${errorText}`);
      }

      const teachersData = await response.json();
      console.log('🔍 [DEBUG] Teachers data loaded:', Object.keys(teachersData));

      console.log('🔍 [DEBUG] Загрузка данных из /api/data/branches');
      const branchesResponse = await fetch('/api/data/branches');
      console.log('🔍 [DEBUG] Branches response status:', branchesResponse.status);
      
      const branchesData = await branchesResponse.json();
      console.log('🔍 [DEBUG] Branches data loaded:', Object.keys(branchesData));

      setData({
        ...teachersData,
        branches: branchesData.branches,
      } as AnalysisResult);
      
      console.log('✅ [DEBUG] Все данные успешно загружены');
    } catch (err) {
      console.error('❌ [DEBUG] Ошибка загрузки:', err);
      setError(err instanceof Error ? err.message : 'Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  // Запуск синхронизации
  const triggerSync = async () => {
    try {
      console.log('🔍 [DEBUG] Запуск синхронизации через POST /api/sync/trigger');
      const response = await fetch('/api/sync/trigger', { method: 'POST' });
      
      console.log('🔍 [DEBUG] Sync response status:', response.status);
      console.log('🔍 [DEBUG] Sync response statusText:', response.statusText);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('🔍 [DEBUG] Sync error body:', errorText);
        throw new Error(`Не удалось запустить синхронизацию (${response.status}): ${errorText}`);
      }

      const result = await response.json();
      console.log('✅ [DEBUG] Синхронизация запущена:', result);

      // Ждем завершения и обновляем данные
      setTimeout(() => {
        fetchData();
      }, 5000);
    } catch (err) {
      console.error('❌ [DEBUG] Ошибка синхронизации:', err);
      setError(err instanceof Error ? err.message : 'Ошибка синхронизации');
    }
  };

  useEffect(() => {
    fetchData();
    // Автообновление каждые 30 секунд
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Загрузка данных...</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white p-8 rounded-lg shadow-md max-w-2xl w-full">
          <div className="text-red-600 text-center mb-4">
            <svg className="w-16 h-16 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h2 className="text-xl font-bold mb-2">Данные не найдены</h2>
            <div className="text-left bg-red-50 border border-red-200 rounded p-4 mb-4">
              <p className="text-sm font-mono text-red-800 break-words">{error}</p>
            </div>
            <div className="text-left bg-yellow-50 border border-yellow-200 rounded p-4 mb-4">
              <p className="text-xs text-yellow-800">
                💡 <strong>DEBUG:</strong> Откройте консоль браузера (F12 → Console), чтобы увидеть детальную информацию об ошибке
              </p>
            </div>
          </div>
          <button
            onClick={triggerSync}
            className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition"
          >
            Запустить синхронизацию
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                📊 Pyrus Dashboard
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Статистика по преподавателям и филиалам
              </p>
            </div>
            <SyncStatus onSync={triggerSync} />
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('oldies')}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm
                ${activeTab === 'oldies'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}
              `}
            >
              👴 Вывод старичков
            </button>
            <button
              onClick={() => setActiveTab('trial')}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm
                ${activeTab === 'trial'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}
              `}
            >
              👶 Конверсия после БПЗ
            </button>
            <button
              onClick={() => setActiveTab('branches')}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm
                ${activeTab === 'branches'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}
              `}
            >
              🏢 Статистика по филиалам
            </button>
          </nav>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {data && activeTab === 'oldies' && (
          <TeachersTable
            groups={data.oldies_groups}
            type="oldies"
          />
        )}

        {data && activeTab === 'trial' && (
          <TeachersTable
            groups={data.trial_groups}
            type="trial"
          />
        )}

        {data && activeTab === 'branches' && (
          <BranchesTable branches={data.branches} />
        )}
      </main>
    </div>
  );
}


