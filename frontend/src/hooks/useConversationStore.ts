'use client';

import { useState, useEffect, useCallback } from 'react';
import { ChatMessageData } from '@/components/chat/ChatMessage';

const STORAGE_KEY = 'omnibus-conversations';
const MESSAGES_STORAGE_KEY = 'omnibus-messages';

export interface ConversationMeta {
    id: string;
    title: string;
    createdAt: string;
    updatedAt: string;
}

export interface GroupedConversations {
    label: string;
    conversations: ConversationMeta[];
}

// Serializable version of ChatMessageData for localStorage
interface StoredMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    citations?: unknown[];
    confidence?: string;
    confidenceScore?: {
        numeric: number;
        label: string;
        top_score: number;
        avg_score: number;
    };
    validation?: {
        is_valid: boolean;
        citation_coverage: number;
        warnings: string[];
        hallucination_risk: 'low' | 'medium' | 'high' | 'refused';
        grounding_score?: number | null;
        ungrounded_claims?: string[];
    };
    processingTime?: number;
    timestamp: string; // ISO string for serialization
}

function loadFromStorage(): ConversationMeta[] {
    if (typeof window === 'undefined') return [];
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function saveToStorage(conversations: ConversationMeta[]) {
    if (typeof window === 'undefined') return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
}

// ─── Message Cache ───────────────────────────────────────────────────

function loadMessagesCache(): Record<string, StoredMessage[]> {
    if (typeof window === 'undefined') return {};
    try {
        const raw = localStorage.getItem(MESSAGES_STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch {
        return {};
    }
}

function saveMessagesCache(cache: Record<string, StoredMessage[]>) {
    if (typeof window === 'undefined') return;
    try {
        localStorage.setItem(MESSAGES_STORAGE_KEY, JSON.stringify(cache));
    } catch {
        // localStorage might be full — evict oldest conversations
        const keys = Object.keys(cache);
        if (keys.length > 10) {
            const trimmed: Record<string, StoredMessage[]> = {};
            // Keep only last 10 conversations
            keys.slice(-10).forEach(k => { trimmed[k] = cache[k]; });
            localStorage.setItem(MESSAGES_STORAGE_KEY, JSON.stringify(trimmed));
        }
    }
}

export function saveMessages(sessionId: string, messages: ChatMessageData[]) {
    const cache = loadMessagesCache();
    cache[sessionId] = messages.map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
        citations: m.citations,
        confidence: m.confidence,
        confidenceScore: m.confidenceScore,
        validation: m.validation,
        processingTime: m.processingTime,
        timestamp: m.timestamp.toISOString(),
    }));
    saveMessagesCache(cache);
}

export function loadMessages(sessionId: string): ChatMessageData[] | null {
    const cache = loadMessagesCache();
    const stored = cache[sessionId];
    if (!stored || stored.length === 0) return null;
    return stored.map(m => ({
        ...m,
        timestamp: new Date(m.timestamp),
    })) as ChatMessageData[];
}

export function deleteMessages(sessionId: string) {
    const cache = loadMessagesCache();
    delete cache[sessionId];
    saveMessagesCache(cache);
}

// ─── Date grouping ───────────────────────────────────────────────────

function groupByDate(conversations: ConversationMeta[]): GroupedConversations[] {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 86400000);
    const sevenDaysAgo = new Date(today.getTime() - 7 * 86400000);

    const groups: Record<string, ConversationMeta[]> = {
        'Hari Ini': [],
        'Kemarin': [],
        '7 Hari Terakhir': [],
        'Lebih Lama': [],
    };

    const sorted = [...conversations].sort(
        (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    );

    for (const conv of sorted) {
        const date = new Date(conv.updatedAt);
        if (date >= today) {
            groups['Hari Ini'].push(conv);
        } else if (date >= yesterday) {
            groups['Kemarin'].push(conv);
        } else if (date >= sevenDaysAgo) {
            groups['7 Hari Terakhir'].push(conv);
        } else {
            groups['Lebih Lama'].push(conv);
        }
    }

    return Object.entries(groups)
        .filter(([, convs]) => convs.length > 0)
        .map(([label, conversations]) => ({ label, conversations }));
}

export function useConversationStore() {
    const [conversations, setConversations] = useState<ConversationMeta[]>([]);
    const [activeId, setActiveId] = useState<string | null>(null);

    // Load from localStorage on mount
    useEffect(() => {
        setConversations(loadFromStorage());
    }, []);

    const persist = useCallback((updated: ConversationMeta[]) => {
        setConversations(updated);
        saveToStorage(updated);
    }, []);

    const addConversation = useCallback((id: string, title: string) => {
        const now = new Date().toISOString();
        const newConv: ConversationMeta = {
            id,
            title: title.slice(0, 60),
            createdAt: now,
            updatedAt: now,
        };
        const updated = [newConv, ...loadFromStorage().filter((c) => c.id !== id)];
        persist(updated);
        setActiveId(id);
        return newConv;
    }, [persist]);

    const updateConversation = useCallback((id: string, updates: Partial<Pick<ConversationMeta, 'title'>>) => {
        const current = loadFromStorage();
        const updated = current.map((c) =>
            c.id === id
                ? { ...c, ...updates, updatedAt: new Date().toISOString() }
                : c
        );
        persist(updated);
    }, [persist]);

    const deleteConversation = useCallback((id: string) => {
        const current = loadFromStorage();
        const updated = current.filter((c) => c.id !== id);
        persist(updated);
        // Also delete cached messages
        deleteMessages(id);
        if (activeId === id) {
            setActiveId(null);
        }
    }, [persist, activeId]);

    const setActiveConversation = useCallback((id: string | null) => {
        setActiveId(id);
    }, []);

    const grouped = groupByDate(conversations);

    return {
        conversations,
        grouped,
        activeId,
        addConversation,
        updateConversation,
        deleteConversation,
        setActiveConversation,
    };
}
