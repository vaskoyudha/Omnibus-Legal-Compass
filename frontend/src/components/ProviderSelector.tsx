'use client';

import React, { useState } from 'react';
import { useProvider } from '@/hooks/useProvider';

interface ProviderSelectorProps {
  onProviderChange?: (provider: string, model: string) => void;
}

export default function ProviderSelector({ onProviderChange }: ProviderSelectorProps) {
  const {
    providers,
    selectedProvider,
    selectedModel,
    isLoading,
    setProvider,
    setModel,
    currentProviderModels,
  } = useProvider();

  const [isLoggingIn, setIsLoggingIn] = useState(false);

  if (isLoading) {
    return (
      <div className="flex flex-col sm:flex-row gap-2 animate-pulse">
        <div
          className="h-7 w-28 rounded"
          style={{ background: 'rgba(255,255,255,0.06)' }}
        />
        <div
          className="h-7 w-36 rounded"
          style={{ background: 'rgba(255,255,255,0.06)' }}
        />
      </div>
    );
  }

  if (!providers.length) return null;

  const chevronSvg = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23666' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`;

  const selectStyle: React.CSSProperties = {
    background: 'rgba(10,10,15,0.9)',
    border: '1px solid rgba(255,255,255,0.1)',
    color: 'white',
    fontSize: '11px',
    fontFamily: 'monospace',
    padding: '3px 22px 3px 8px',
    borderRadius: '6px',
    appearance: 'none',
    WebkitAppearance: 'none',
    backgroundImage: chevronSvg,
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 6px center',
    cursor: 'pointer',
    outline: 'none',
  };

  const buttonStyle: React.CSSProperties = {
    background: 'rgba(50, 100, 255, 0.2)',
    border: '1px solid rgba(50, 100, 255, 0.4)',
    color: '#aaccff',
    fontSize: '11px',
    fontFamily: 'monospace',
    padding: '3px 10px',
    borderRadius: '6px',
    cursor: 'pointer',
    outline: 'none',
    whiteSpace: 'nowrap',
    transition: 'all 0.2s ease',
  };

  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newProvider = e.target.value;
    setProvider(newProvider);
    const prov = providers.find((p) => p.id === newProvider);
    const firstModel = prov?.models[0]?.id || '';
    onProviderChange?.(newProvider, firstModel);
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newModel = e.target.value;
    setModel(newModel);
    onProviderChange?.(selectedProvider, newModel);
  };

  const hasAntigravity = providers.some(p => p.id === 'antigravity');

  const handleAntigravityLogin = async () => {
    setIsLoggingIn(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${baseUrl}/api/v1/auth/antigravity/login`);
      const data = await res.json();
      
      if (data.url) {
        window.open(data.url, '_blank');
        
        const pollInterval = setInterval(async () => {
          const statusRes = await fetch(`${baseUrl}/api/v1/auth/antigravity/status`);
          const statusData = await statusRes.json();
          
          if (statusData.status === 'success') {
            clearInterval(pollInterval);
            alert('Successfully logged in to Antigravity!');
            window.location.reload();
          } else if (statusData.status === 'error') {
            clearInterval(pollInterval);
            setIsLoggingIn(false);
            alert('Login failed: ' + statusData.message);
          }
        }, 2000);
      }
    } catch (e) {
      console.error('Login failed', e);
      setIsLoggingIn(false);
      alert('Failed to connect to backend.');
    }
  };

  return (
    <div className="flex flex-col sm:flex-row gap-2 items-start sm:items-center">
      <select
        value={selectedProvider}
        onChange={handleProviderChange}
        style={selectStyle}
        aria-label="Select LLM Provider"
      >
        {providers.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>

      {currentProviderModels.length > 0 && (
        <select
          value={selectedModel}
          onChange={handleModelChange}
          style={selectStyle}
          aria-label="Select Model"
        >
          {currentProviderModels.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
      )}

      {!hasAntigravity && (
        <button 
          onClick={handleAntigravityLogin} 
          style={buttonStyle}
          disabled={isLoggingIn}
          title="Login to Antigravity to enable free Gemini & Claude models"
        >
          {isLoggingIn ? 'Waiting...' : '⚡ Connect Antigravity'}
        </button>
      )}
    </div>
  );
}
