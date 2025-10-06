/**
 * Таблица преподавателей с группировкой и призами
 * Аналог вкладок Excel "Вывод старичков" и "Конверсия после БПЗ"
 */

'use client';

import type { TeacherStats } from '../lib/types';

interface Props {
  groups: {
    [key: string]: TeacherStats[];
  };
  type: 'oldies' | 'trial';
}

const PRIZES_CONFIG = {
  oldies: {
    '35+': { prizes: ['📱 iPad', '📲 HonorPad', '📲 HonorPad', '📲 HonorPad'], count: 4 },
    '16-34': { prize: '📲 HonorPad', count: 3 },
    '6-15': { prize: '💎 Tg Premium', count: 3 },
  },
  trial: {
    '16+': { prizes: ['📱 iPad', '📲 HonorPad', '📲 HonorPad', '📲 HonorPad'], count: 4 },
    '11-15': { prize: '📲 HonorPad', count: 3 },
    '5-10': { prize: '💎 Tg Premium', count: 3 },
  },
};

const GROUP_EMOJIS = {
  '35+': '🥇',
  '16-34': '🥈',
  '6-15': '🥉',
  '16+': '🥇',
  '11-15': '🥈',
  '5-10': '🥉',
};

export function TeachersTable({ groups, type }: Props) {
  const groupKeys = Object.keys(groups);
  const config = PRIZES_CONFIG[type];

  return (
    <div className="space-y-8">
      {/* Информация */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          Учитываются формы со статусом PE: Start, Future, PE 5, Китайский. 
          Процент = доля форм со статусом "учится".
        </p>
      </div>

      {groupKeys.map((groupName) => {
        const teachers = groups[groupName];
        if (!teachers || teachers.length === 0) return null;

        const groupConfig = config[groupName as keyof typeof config];
        const emoji = GROUP_EMOJIS[groupName as keyof typeof GROUP_EMOJIS] || '📋';

        return (
          <div key={groupName} className="bg-white rounded-lg shadow-md overflow-hidden">
            {/* Заголовок группы */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4">
              <h2 className="text-xl font-bold text-white">
                {emoji} Группа {groupName} {type === 'oldies' ? 'студентов' : 'БПЗ студентов'}
              </h2>
            </div>

            {/* Таблица */}
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      № / 👨‍🏫 Преподаватель
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      📊 Всего
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      🎓 Учится
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      📈 %
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      🏆 Приз
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {teachers.map((teacher, index) => {
                    const isPrizeWinner = index < (groupConfig?.count || 0);
                    let prize = '';

                    if (isPrizeWinner && groupConfig) {
                      if ('prizes' in groupConfig) {
                        prize = groupConfig.prizes[index];
                      } else {
                        prize = groupConfig.prize;
                      }
                    }

                    const percentage = type === 'oldies' 
                      ? teacher.return_percentage 
                      : teacher.conversion_percentage;

                    const total = type === 'oldies'
                      ? teacher.form_2304918_total
                      : teacher.form_792300_total;

                    const studying = type === 'oldies'
                      ? teacher.form_2304918_studying
                      : teacher.form_792300_studying;

                    return (
                      <tr
                        key={teacher.name}
                        className={isPrizeWinner ? 'bg-yellow-50' : 'hover:bg-gray-50'}
                      >
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <span className="text-sm font-medium text-gray-500 mr-3">
                              {index + 1}.
                            </span>
                            <span className="text-sm font-medium text-gray-900">
                              {teacher.name}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
                          {total}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
                          {studying}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                          <span className={`text-sm font-semibold ${
                            percentage >= 70 ? 'text-green-600' :
                            percentage >= 50 ? 'text-yellow-600' :
                            'text-red-600'
                          }`}>
                            {percentage.toFixed(2)}%
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
        );
      })}
    </div>
  );
}


