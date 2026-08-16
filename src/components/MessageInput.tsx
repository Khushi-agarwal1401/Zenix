import { useState } from 'react';
import { Send, Sparkles } from 'lucide-react';
import clsx from 'clsx';

interface MessageInputProps {
    onSend: (message: string) => void;
    isLoading?: boolean;
}

export function MessageInput({ onSend, isLoading }: MessageInputProps) {
    const [input, setInput] = useState('');

    const handleSend = () => {
        if (input.trim() && !isLoading) {
            onSend(input);
            setInput('');
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="p-4 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md border-t border-zinc-200 dark:border-zinc-800">
            <div className="max-w-3xl mx-auto flex gap-2 relative">
                <div className="relative flex-1">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask Zenix anything..."
                        disabled={isLoading}
                        className="w-full pl-6 pr-14 py-4 rounded-full border border-zinc-200 dark:border-zinc-700/50 bg-zinc-50 dark:bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-all shadow-sm placeholder:text-zinc-400"
                    />
                    <div className="absolute right-3 top-1/2 -translate-y-1/2">
                        {isLoading ? (
                            <div className="w-8 h-8 flex items-center justify-center">
                                <Sparkles className="w-5 h-5 text-purple-500 animate-spin" />
                            </div>
                        ) : (
                            <button
                                onClick={handleSend}
                                disabled={!input.trim()}
                                className={clsx(
                                    "w-10 h-10 flex items-center justify-center rounded-full transition-all duration-200",
                                    input.trim()
                                        ? "bg-black text-white dark:bg-white dark:text-black hover:scale-105 active:scale-95"
                                        : "bg-zinc-200 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-600 cursor-not-allowed"
                                )}
                            >
                                <Send className="w-4 h-4 ml-0.5" />
                            </button>
                        )}
                    </div>
                </div>
            </div>
            <div className="max-w-3xl mx-auto mt-2 text-center">
                <p className="text-[10px] text-zinc-400 dark:text-zinc-600">
                    Zenix can make mistakes. Check important info.
                </p>
            </div>
        </div>
    );
}
