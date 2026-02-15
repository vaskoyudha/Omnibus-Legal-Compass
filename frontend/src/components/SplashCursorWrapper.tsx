'use client';

import dynamic from 'next/dynamic';

const SplashCursor = dynamic(
  () => import('@/components/reactbits/SplashCursor'),
  { ssr: false }
);

export default function SplashCursorWrapper() {
  return (
    <div className="fixed inset-0 z-[2] pointer-events-none" aria-hidden="true">
      <SplashCursor TRANSPARENT={true} />
    </div>
  );
}
