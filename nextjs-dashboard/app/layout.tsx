/**
 * Root Layout для Next.js 13+ App Router
 */

import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Pyrus Dashboard',
  description: 'Статистика по преподавателям и филиалам из Pyrus',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}


