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
        <div className="px-4 pb-4 pt-2 bg-white/90 dark:bg-zinc-950/90 backdrop-blur-2xl border-t border-zinc-200/50 dark:border-zinc-800/50 z-20 relative">
            <div className="max-w-3xl mx-auto flex gap-3 relative">
                <div className="relative flex-1">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask Zenix anything..."
                        disabled={isLoading}
                        className="w-full pl-5 pr-14 py-3.5 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400 dark:focus:border-violet-500 transition-all shadow-sm placeholder:text-zinc-400 dark:placeholder:text-zinc-500 text-[15px]"
                    />
                    <div className="absolute right-2.5 top-1/2 -translate-y-1/2">
                        {isLoading ? (
                            <div className="w-9 h-9 flex items-center justify-center">
                                <Sparkles className="w-4.5 h-4.5 text-violet-500 animate-spin" />
                            </div>
                        ) : (
                            <button
                                onClick={handleSend}
                                disabled={!input.trim()}
                                className={clsx(
                                    "w-9 h-9 flex items-center justify-center rounded-xl transition-all duration-200",
                                    input.trim()
                                        ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 hover:shadow-md hover:shadow-zinc-900/10 dark:hover:shadow-zinc-100/10 active:scale-95"
                                        : "bg-zinc-100 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-600 cursor-not-allowed"
                                )}
                                aria-label="Send message"
                            >
                                <Send className="w-4 h-4" />
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
