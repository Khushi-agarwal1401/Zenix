"use client";

import { useState } from 'react';
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
            content: `Namaste! I am Zenix. How can I help you today? \n\nI can switch between a **Desi** friend and a **Sarkari** assistant depending on your needs.`,
            timestamp: new Date().toISOString(),
            persona: 'desi'
        }
    ]);
    const [isLoading, setIsLoading] = useState(false);

    const handleSend = async (content: string) => {
        // Add user message
        const userMsg: Message = {
            id: Date.now().toString(),
            role: 'user',
            content,
            timestamp: new Date().toISOString()
        };

        setMessages(prev => [...prev, userMsg]);
        setIsLoading(true);

        // Simulate AI response using the service
        try {
            const { response: responseText, requestId } = await AIResponseService.generateResponse(content, persona);

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
            console.error("Failed to generate response:", error);
            // Optional: Add error handling UI or toast here
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-screen bg-zinc-50 dark:bg-black text-foreground font-sans">
            {/* Header */}
            <header className="flex items-center justify-between px-6 py-4 bg-white/60 dark:bg-zinc-950/60 border-b border-white/20 dark:border-zinc-800/50 backdrop-blur-xl sticky top-0 z-20 shadow-[0_10px_40px_rgba(0,0,0,0.03)] dark:shadow-[0_10px_40px_rgba(0,0,0,0.2)]">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-black dark:bg-white flex items-center justify-center">
                        <span className="text-white dark:text-black font-bold text-lg">Z</span>
                    </div>
                    <h1 className="font-semibold text-lg tracking-tight">Zenix</h1>
                    <span className="px-2 py-0.5 rounded-md bg-zinc-100 dark:bg-zinc-800 text-xs font-medium text-zinc-500 border border-zinc-200 dark:border-zinc-700">
                        Beta
                    </span>
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
