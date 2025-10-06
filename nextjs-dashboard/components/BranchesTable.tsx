/**
 * Таблица статистики по филиалам
 * Аналог вкладки Excel "Статистика по филиалам"
 */

'use client';

import type { BranchStats } from '../lib/types';

interface Props {
  branches: BranchStats[];
}

const BRANCH_PRIZES = [
  '📱 Interactive Display',
  '☕ Кофемашина + 2 кг кофе',
  '☕ Кофемашина',
  '💰 20 000 руб.',
  '💰 10 000 руб.',
];

export function BranchesTable({ branches }: Props) {
  return (
    <div className="space-y-6">
      {/* Информация */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          Суммарная статистика по филиалам (статус PE: Start, Future, PE 5, Китайский). 
          Итоговый % = % возврата старичков + % конверсии после БПЗ.
        </p>
      </div>

      {/* Таблица */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="bg-gradient-to-r from-purple-600 to-purple-700 px-6 py-4">
          <h2 className="text-xl font-bold text-white">
            🏢 Статистика по филиалам
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  № / 🏢 Филиал
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  👴 Ст: Всего
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  🎓 Ст: Учится
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  📊 Ст: %
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  👶 Нов.: Всего
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  🎓 Нов.: Учится
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  📊 Нов.: %
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  🏆 Итого %
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  🎁 Приз
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {branches.map((branch, index) => {
                const prize = index < BRANCH_PRIZES.length ? BRANCH_PRIZES[index] : '';
                const isPrizeWinner = prize !== '';

                return (
                  <tr
                    key={branch.name}
                    className={isPrizeWinner ? 'bg-yellow-50' : 'hover:bg-gray-50'}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <span className="text-sm font-medium text-gray-500 mr-3">
                          {index + 1}.
                        </span>
                        <span className="text-sm font-medium text-gray-900">
                          {branch.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
                      {branch.form_2304918_total}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
                      {branch.form_2304918_studying}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium text-blue-600">
                      {branch.return_percentage.toFixed(2)}%
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
                      {branch.form_792300_total}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
                      {branch.form_792300_studying}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium text-purple-600">
                      {branch.conversion_percentage.toFixed(2)}%
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className={`text-sm font-bold ${
                        branch.total_percentage >= 140 ? 'text-green-600' :
                        branch.total_percentage >= 100 ? 'text-yellow-600' :
                        'text-red-600'
                      }`}>
                        {branch.total_percentage.toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm">
                      {prize && (
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                          {prize}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Исключенные филиалы */}
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="text-sm font-bold text-red-800 mb-2">
          Филиалы, исключенные из соревнования:
        </h3>
        <ul className="text-sm text-red-700 space-y-1">
          <li>• Макеева 15</li>
          <li>• Коммуны 106/1</li>
          <li>• Славы 30</li>
          <li>• Online</li>
        </ul>
      </div>
    </div>
  );
}


