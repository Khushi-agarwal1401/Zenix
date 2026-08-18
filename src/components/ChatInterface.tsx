"use client";

import React, { useState } from 'react';
import { Persona, Message } from '@/lib/types';
import { PersonaToggle } from './PersonaToggle';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';

import { AIResponseService } from '@/lib/ai_service';

export default function ChatInterface() {
    const [persona, setPersona] = useState<Persona>('desi');
    const [messages, setMessages] = useState<Message[]>([
        {
            id: 'welcome',
            role: 'assistant',
            content: `Namaste! I am Zenix. How can I help you today?\n\nI can switch between a **Desi** friend and a **Sarkari** assistant depending on your needs.`,
            timestamp: new Date().toISOString(),
            persona: 'desi'
        }
    ]);
    const [isLoading, setIsLoading] = useState(false);

    const handleSend = React.useCallback(async (content: string) => {
        // Add user message
        const userMsg: Message = {
            id: Date.now().toString(),
            role: 'user',
            content,
            timestamp: new Date().toISOString()
        };

        setMessages(prev => [...prev, userMsg]);
        setIsLoading(true);

        try {
            const { response: responseText, requestId } = await AIResponseService.generateResponse(content, persona, messages);

            const aiMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: responseText,
                timestamp: new Date().toISOString(),
                persona,
                requestId
            };

            setMessages(prev => [...prev, aiMsg]);
        } catch (error) {
            console.error('Error generating response:', error);
            setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: `Sorry, something went wrong. Please try again.\n\nError: ${error instanceof Error ? error.message : 'Unknown error'}`,
                timestamp: new Date().toISOString(),
                isError: true,
            }]);
        } finally {
            setIsLoading(false);
        }
    }, [persona, messages]);



    return (
        <div className="flex flex-col h-screen bg-zinc-50 dark:bg-zinc-950 text-foreground font-sans">
            {/* Header */}
            <header className="flex items-center justify-between px-6 py-3.5 bg-white/80 dark:bg-zinc-950/80 border-b border-zinc-200/60 dark:border-zinc-800/60 backdrop-blur-2xl sticky top-0 z-20">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
                        <span className="text-white font-bold text-base">Z</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <h1 className="font-semibold text-lg tracking-tight">Zenix</h1>
                        <span className="px-2 py-0.5 rounded-full bg-violet-50 dark:bg-violet-950/50 text-[10px] font-medium text-violet-600 dark:text-violet-400 border border-violet-200/50 dark:border-violet-800/50 uppercase tracking-wider">
                            Beta
                        </span>
                    </div>
                </div>
                <PersonaToggle currentPersona={persona} onToggle={setPersona} />
            </header>

            {/* Chat Area */}
            <MessageList messages={messages} isLoading={isLoading} />

            {/* Input Area */}
            <MessageInput onSend={handleSend} isLoading={isLoading} />
        </div>
    );
}
