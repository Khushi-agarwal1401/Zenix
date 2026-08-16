import React from 'react';
import ReactMarkdown from 'react-markdown';
import clsx from 'clsx';
import { Bot, User, Copy, Check, ThumbsUp, ThumbsDown } from 'lucide-react';
import { Message } from '@/lib/types';

interface MessageListProps {
    messages: Message[];
    isLoading?: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
    const [copiedId, setCopiedId] = React.useState<string | null>(null);
    const [feedbackState, setFeedbackState] = React.useState<Record<string, 'up' | 'down'>>({});
    
    // Refs for fallback IntersectionObserver (scroll indicators)
    const scrollerRef = React.useRef<HTMLDivElement>(null);
    const topSentinelRef = React.useRef<HTMLDivElement>(null);
    const bottomSentinelRef = React.useRef<HTMLDivElement>(null);

    React.useEffect(() => {
        if (typeof CSS !== 'undefined' && CSS.supports('container-type', 'scroll-state')) {
            return; // Native support, no observer needed
        }

        const scroller = scrollerRef.current;
        const topSentinel = topSentinelRef.current;
        const bottomSentinel = bottomSentinelRef.current;

        if (!scroller || !topSentinel || !bottomSentinel) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.target === topSentinel) {
                    scroller.classList.toggle('scrolled-down', !entry.isIntersecting);
                }
                if (entry.target === bottomSentinel) {
                    scroller.classList.toggle('can-scroll-down', !entry.isIntersecting);
                }
            });
        }, { root: scroller });

        observer.observe(topSentinel);
        observer.observe(bottomSentinel);

        return () => observer.disconnect();
    }, []);

    const handleCopy = async (id: string, content: string) => {
        try {
            await navigator.clipboard.writeText(content);
            setCopiedId(id);
            setTimeout(() => setCopiedId(null), 2000);
        } catch (err) {
            console.error('Failed to copy text: ', err);
        }
    };

    const handleFeedback = async (requestId: string, feedback: 'up' | 'down') => {
        if (!requestId) return;

        try {
            await fetch('http://127.0.0.1:8000/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ request_id: requestId, feedback }),
            });

            setFeedbackState(prev => ({ ...prev, [requestId]: feedback }));
        } catch (err) {
            console.error('Failed to send feedback:', err);
        }
    };

    return (
        <div ref={scrollerRef} className="flex-1 scroller space-y-6 p-4">
            <div ref={topSentinelRef} className="h-0 w-0 absolute top-0" />
            <div className="indicator-top" />
            {messages.map((msg, index) => (
                <div
                    key={msg.id}
                    style={index === messages.length - 1 ? { scrollInitialTarget: 'nearest' } as React.CSSProperties : undefined}
                    className={clsx(
                        "flex gap-4 max-w-3xl mx-auto group animate-message-enter",
                        msg.role === 'user' ? "justify-end" : "justify-start"
                    )}
                >
                    {msg.role === 'assistant' && (
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shrink-0 mt-1 shadow-md">
                            <Bot className="w-5 h-5" />
                        </div>
                    )}

                    <div
                        className={clsx(
                            "relative px-5 py-3 rounded-2xl max-w-[85%] text-sm sm:text-base shadow-sm group-hover:shadow-md transition-shadow",
                            msg.role === 'user'
                                ? "bg-black text-white dark:bg-white dark:text-black rounded-tr-sm"
                                : "bg-white border border-zinc-200 dark:bg-zinc-900 dark:border-zinc-700 text-zinc-800 dark:text-zinc-200 rounded-tl-sm ring-1 ring-black/5"
                        )}
                    >
                        <div className="prose prose-sm dark:prose-invert max-w-none break-words">
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                        <div className="flex items-center justify-end gap-2 mt-2">

                            {/* Feedback Buttons (Only for Assistant with Request ID) */}
                            {msg.role === 'assistant' && msg.requestId && (
                                <div className="flex gap-1 mr-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button
                                        onClick={() => handleFeedback(msg.requestId!, 'up')}
                                        className={clsx(
                                            "p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors",
                                            feedbackState[msg.requestId!] === 'up' ? "text-green-600" : "text-zinc-400 hover:text-green-600"
                                        )}
                                        disabled={!!feedbackState[msg.requestId!]}
                                    >
                                        <ThumbsUp className="w-3 h-3" />
                                    </button>
                                    <button
                                        onClick={() => handleFeedback(msg.requestId!, 'down')}
                                        className={clsx(
                                            "p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors",
                                            feedbackState[msg.requestId!] === 'down' ? "text-red-600" : "text-zinc-400 hover:text-red-600"
                                        )}
                                        disabled={!!feedbackState[msg.requestId!]}
                                    >
                                        <ThumbsDown className="w-3 h-3" />
                                    </button>
                                </div>
                            )}

                            <p suppressHydrationWarning className="text-[10px] opacity-50 text-right">
                                {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </p>
                            <button
                                onClick={() => handleCopy(msg.id, msg.content)}
                                className={clsx(
                                    "p-1 rounded-full transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100",
                                    msg.role === 'user'
                                        ? "hover:bg-white/20 text-white/70 hover:text-white"
                                        : "hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 hover:text-zinc-600 dark:text-zinc-500 dark:hover:text-zinc-300"
                                )}
                                aria-label="Copy message"
                            >
                                {copiedId === msg.id ? (
                                    <Check className="w-3 h-3" />
                                ) : (
                                    <Copy className="w-3 h-3" />
                                )}
                            </button>
                        </div>
                    </div>

                    {msg.role === 'user' && (
                        <div className="w-8 h-8 rounded-full bg-zinc-200 dark:bg-zinc-700 flex items-center justify-center text-zinc-600 dark:text-zinc-300 shrink-0 mt-1">
                            <User className="w-5 h-5" />
                        </div>
                    )}
                </div>
            ))}

            {isLoading && (
                <div className="flex gap-4 max-w-3xl mx-auto justify-start animate-pulse">
                    <div className="w-8 h-8 rounded-full bg-zinc-200 dark:bg-zinc-800 shrink-0 mt-1"></div>
                    <div className="bg-zinc-100 dark:bg-zinc-800 rounded-2xl px-5 py-4 w-32 h-10"></div>
                </div>
            )}
            <div className="indicator-bottom" />
            <div ref={bottomSentinelRef} className="h-0 w-0 absolute bottom-0" />
        </div>
    );
}
