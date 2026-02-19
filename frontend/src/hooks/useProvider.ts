'use client';

import { useState, useEffect, useCallback } from 'react';

export interface ModelInfo {
  id: string;
  name: string;
  context_window: number;
  supports_streaming: boolean;
}

export interface ProviderInfo {
  id: string;
  name: string;
  is_available: boolean;
  models: ModelInfo[];
}

const STORAGE_KEY_PROVIDER = 'omnibus_provider';
const STORAGE_KEY_MODEL = 'omnibus_model';

export function useProvider() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [selectedProvider, setSelectedProviderState] = useState<string>('copilot');
  const [selectedModel, setSelectedModelState] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);

  // Fetch providers from backend on mount
  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    fetch(`${apiUrl}/api/v1/providers`)
      .then((r) => r.json())
      .then((data) => {
        const available: ProviderInfo[] = (data.providers || []).filter(
          (p: ProviderInfo) => p.is_available
        );
        setProviders(available);

        // Restore from localStorage or pick first available
        const savedProvider = localStorage.getItem(STORAGE_KEY_PROVIDER);
        const savedModel = localStorage.getItem(STORAGE_KEY_MODEL);

        const validProvider = available.find((p) => p.id === savedProvider) || available[0];
        if (validProvider) {
          setSelectedProviderState(validProvider.id);
          const validModel =
            validProvider.models.find((m) => m.id === savedModel) || validProvider.models[0];
          if (validModel) {
            setSelectedModelState(validModel.id);
          }
        }
      })
      .catch(() => {
        // Silent fail — backend might not be running
      })
      .finally(() => setIsLoading(false));
  }, []);

  const setProvider = useCallback(
    (providerId: string) => {
      setSelectedProviderState(providerId);
      localStorage.setItem(STORAGE_KEY_PROVIDER, providerId);
      // Auto-select first model of new provider
      const provider = providers.find((p) => p.id === providerId);
      const firstModel = provider?.models[0]?.id || '';
      setSelectedModelState(firstModel);
      localStorage.setItem(STORAGE_KEY_MODEL, firstModel);
    },
    [providers]
  );

  const setModel = useCallback((modelId: string) => {
    setSelectedModelState(modelId);
    localStorage.setItem(STORAGE_KEY_MODEL, modelId);
  }, []);

  const currentProviderModels =
    providers.find((p) => p.id === selectedProvider)?.models || [];

  return {
    providers,
    selectedProvider,
    selectedModel,
    isLoading,
    setProvider,
    setModel,
    currentProviderModels,
  };
}
