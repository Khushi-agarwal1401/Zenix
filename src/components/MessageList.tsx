import React from 'react';
import ReactMarkdown, { Components } from 'react-markdown';
import clsx from 'clsx';
import { Bot, User, Copy, Check, ThumbsUp, ThumbsDown, ArrowDown } from 'lucide-react';
import { Message } from '@/lib/types';

interface MessageListProps {
    messages: Message[];
    isLoading?: boolean;
}

/* ── Custom Markdown Components ────────────────────────────────── */

function CodeBlock({ className, children, ...props }: React.HTMLAttributes<HTMLPreElement> & { children?: React.ReactNode }) {
    void props;
    const [copied, setCopied] = React.useState(false);
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : '';

    const handleCopy = async () => {
        const text = typeof children === 'string'
            ? children
            : React.Children.toArray(children)
                .map(c => {
                    if (typeof c === 'string') return c;
                    if (React.isValidElement(c)) {
                        const props = c.props as Record<string, unknown>;
                        return props.children ?? '';
                    }
                    return '';
                })
                .join('');
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {}
    };

    return (
        <div className="code-block group/code relative my-3">
            {language && (
                <div className="absolute top-0 left-0 px-2.5 py-0.5 text-[10px] font-mono font-medium text-zinc-400 dark:text-zinc-500 uppercase tracking-wider bg-zinc-100 dark:bg-zinc-800 rounded-br-lg rounded-tl-lg border-b border-r border-zinc-200/50 dark:border-zinc-700/50">
                    {language}
                </div>
            )}
            <button
                onClick={handleCopy}
                className="absolute top-2 right-2 p-1.5 rounded-md bg-zinc-200/80 dark:bg-zinc-700/80 text-zinc-500 dark:text-zinc-400 hover:bg-zinc-300 dark:hover:bg-zinc-600 opacity-0 group-hover/code:opacity-100 transition-all duration-200"
                aria-label="Copy code"
            >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
            <pre className={clsx("overflow-x-auto rounded-xl text-[13px] leading-relaxed", className)} {...props}>
                {children}
            </pre>
        </div>
    );
}

const markdownComponents: Components = {
    pre: ({ children, ...props }) => {
        // If the child is a code element, use our CodeBlock wrapper
        const child = React.Children.toArray(children)[0] as React.ReactElement<Record<string, unknown>>;
        if (child && child.type === 'code') {
            const codeProps = child.props as { className?: string; children?: React.ReactNode };
            return (
                <CodeBlock className={codeProps.className}>
                    {codeProps.children}
                </CodeBlock>
            );
        }
        return <pre {...props}>{children}</pre>;
    },
    code: ({ className, children, ...props }) => {
        const isInline = !className;
        if (isInline) {
            return (
                <code className="px-1.5 py-0.5 rounded-md bg-zinc-100 dark:bg-zinc-800 text-[13px] font-mono text-violet-600 dark:text-violet-400 border border-zinc-200/50 dark:border-zinc-700/50" {...props}>
                    {children}
                </code>
            );
        }
        return <code className={className} {...props}>{children}</code>;
    },
};

/* ── Helpers ───────────────────────────────────────────────────── */

function formatDateGroup(timestamp: string): string {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined });
}

function getDateKey(timestamp: string): string {
    const d = new Date(timestamp);
    return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

/* ── Component ─────────────────────────────────────────────────── */

export function MessageList({ messages, isLoading }: MessageListProps) {
    const [copiedId, setCopiedId] = React.useState<string | null>(null);
    const [feedbackState, setFeedbackState] = React.useState<Record<string, 'up' | 'down'>>({});
    const [showScrollBtn, setShowScrollBtn] = React.useState(false);
    const [isNearBottom, setIsNearBottom] = React.useState(true);

    const scrollerRef = React.useRef<HTMLDivElement>(null);
    const topSentinelRef = React.useRef<HTMLDivElement>(null);
    const bottomSentinelRef = React.useRef<HTMLDivElement>(null);
    const bottomRef = React.useRef<HTMLDivElement>(null);

    /* ── Auto-scroll on new message ── */
    React.useEffect(() => {
        if (isNearBottom && bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isLoading, isNearBottom]);

    /* ── Scroll detection (top/bottom indicators + scroll-to-bottom button) ── */
    React.useEffect(() => {
        const scroller = scrollerRef.current;
        const topSentinel = topSentinelRef.current;
        const bottomSentinel = bottomSentinelRef.current;
        if (!scroller) return;

        // Native scroll-state support
        if (typeof CSS !== 'undefined' && CSS.supports('container-type', 'scroll-state')) {
            // Still need scroll-to-bottom detection via scroll event
            const handleScroll = () => {
                const { scrollTop, scrollHeight, clientHeight } = scroller;
                const atBottom = scrollHeight - scrollTop - clientHeight < 80;
                setIsNearBottom(atBottom);
                setShowScrollBtn(!atBottom);
            };
            scroller.addEventListener('scroll', handleScroll, { passive: true });
            return () => scroller.removeEventListener('scroll', handleScroll);
        }

        // Fallback: IntersectionObserver
        if (!topSentinel || !bottomSentinel) return;

        const handleScroll = () => {
            const { scrollTop, scrollHeight, clientHeight } = scroller;
            const atBottom = scrollHeight - scrollTop - clientHeight < 80;
            setIsNearBottom(atBottom);
            setShowScrollBtn(!atBottom);
        };
        scroller.addEventListener('scroll', handleScroll, { passive: true });

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

        return () => {
            observer.disconnect();
            scroller.removeEventListener('scroll', handleScroll);
        };
    }, []);

    const scrollToBottom = () => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    /* ── Handlers ── */

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

    /* ── Render ── */

    return (
        <div ref={scrollerRef} className="flex-1 scroller space-y-0.5 px-4 py-6 bg-dot-pattern relative">
            <div ref={topSentinelRef} className="h-0 w-0 absolute top-0" />
            <div className="indicator-top" />

            {/* ── Messages ── */}
            {messages.map((msg, index) => {
                const prevMsg = index > 0 ? messages[index - 1] : null;
                const nextMsg = index < messages.length - 1 ? messages[index + 1] : null;
                const isFirstInGroup = !prevMsg || prevMsg.role !== msg.role;
                const isLastInGroup = !nextMsg || nextMsg.role !== msg.role;
                const dateKey = getDateKey(msg.timestamp);
                const prevDateKey = prevMsg ? getDateKey(prevMsg.timestamp) : null;
                const showDateSeparator = dateKey !== prevDateKey;

                return (
                    <React.Fragment key={msg.id}>
                        {/* Date separator */}
                        {showDateSeparator && (
                            <div className="flex items-center gap-3 py-4">
                                <div className="flex-1 h-px bg-zinc-200/60 dark:bg-zinc-800/60" />
                                <span className="text-[11px] font-medium text-zinc-400 dark:text-zinc-500 select-none px-1">
                                    {formatDateGroup(msg.timestamp)}
                                </span>
                                <div className="flex-1 h-px bg-zinc-200/60 dark:bg-zinc-800/60" />
                            </div>
                        )}

                        <div
                            style={index === messages.length - 1 ? { scrollInitialTarget: 'nearest' } as React.CSSProperties : undefined}
                            className={clsx(
                                "flex max-w-3xl mx-auto group animate-message-enter",
                                msg.role === 'user' ? "justify-end" : "justify-start",
                                // Tighter spacing for consecutive messages from same sender
                                !isFirstInGroup && "mt-1",
                                isFirstInGroup && "mt-4",
                            )}
                        >
                            {/* Bot avatar — only on first in group */}
                            {msg.role === 'assistant' && (
                                <div className={clsx(
                                    "w-8 h-8 shrink-0 transition-opacity duration-200",
                                    !isFirstInGroup ? "invisible" : "mt-0.5"
                                )}>
                                    {isFirstInGroup ? (
                                        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-violet-500/25">
                                            <Bot className="w-4 h-4" />
                                        </div>
                                    ) : null}
                                </div>
                            )}

                            <div
                                className={clsx(
                                    "relative px-4 py-3 text-sm sm:text-[15px] leading-relaxed transition-all duration-200 max-w-[82%]",
                                    msg.role === 'user'
                                        ? clsx(
                                            "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 shadow-lg shadow-zinc-900/10 dark:shadow-zinc-100/10",
                                            // Roundness: first/last in group get more rounding
                                            isFirstInGroup && isLastInGroup && "rounded-2xl",
                                            isFirstInGroup && !isLastInGroup && "rounded-2xl rounded-br-md",
                                            !isFirstInGroup && isLastInGroup && "rounded-2xl rounded-tr-md",
                                            !isFirstInGroup && !isLastInGroup && "rounded-2xl rounded-r-md",
                                        )
                                        : clsx(
                                            "bg-white dark:bg-zinc-900 text-zinc-800 dark:text-zinc-200 shadow-sm ring-1 ring-zinc-900/[0.04] dark:ring-white/[0.06] border border-zinc-100 dark:border-zinc-800",
                                            isFirstInGroup && isLastInGroup && "rounded-2xl",
                                            isFirstInGroup && !isLastInGroup && "rounded-2xl rounded-bl-md",
                                            !isFirstInGroup && isLastInGroup && "rounded-2xl rounded-tl-md",
                                            !isFirstInGroup && !isLastInGroup && "rounded-2xl rounded-l-md",
                                        )
                                )}
                            >
                                <div className="prose prose-sm dark:prose-invert max-w-none break-words prose-p:leading-relaxed prose-pre:bg-zinc-100 dark:prose-pre:bg-zinc-800">
                                    <ReactMarkdown components={markdownComponents}>{msg.content}</ReactMarkdown>
                                </div>

                                {/* Meta row — only on last message in group */}
                                {isLastInGroup && (
                                    <div className="flex items-center justify-end gap-1.5 mt-2">
                                        {/* Persona badge for assistant */}
                                        {msg.role === 'assistant' && msg.persona && (
                                            <span className={clsx(
                                                "text-[10px] font-medium px-1.5 py-0.5 rounded-md mr-1",
                                                msg.persona === 'desi'
                                                    ? "bg-amber-50 text-amber-600 dark:bg-amber-950/30 dark:text-amber-400"
                                                    : "bg-sky-50 text-sky-600 dark:bg-sky-950/30 dark:text-sky-400"
                                            )}>
                                                {msg.persona === 'desi' ? '☕ Desi' : '📋 Sarkari'}
                                            </span>
                                        )}

                                        {/* Feedback buttons */}
                                        {msg.role === 'assistant' && msg.requestId && (
                                            <div className="flex gap-0.5 mr-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                                                <button
                                                    onClick={() => handleFeedback(msg.requestId!, 'up')}
                                                    className={clsx(
                                                        "p-1.5 rounded-lg transition-all duration-200",
                                                        feedbackState[msg.requestId!] === 'up'
                                                            ? "text-emerald-500 bg-emerald-50 dark:bg-emerald-950/30"
                                                            : "text-zinc-400 hover:text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-950/30"
                                                    )}
                                                    disabled={!!feedbackState[msg.requestId!]}
                                                >
                                                    <ThumbsUp className="w-3.5 h-3.5" />
                                                </button>
                                                <button
                                                    onClick={() => handleFeedback(msg.requestId!, 'down')}
                                                    className={clsx(
                                                        "p-1.5 rounded-lg transition-all duration-200",
                                                        feedbackState[msg.requestId!] === 'down'
                                                            ? "text-red-500 bg-red-50 dark:bg-red-950/30"
                                                            : "text-zinc-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30"
                                                    )}
                                                    disabled={!!feedbackState[msg.requestId!]}
                                                >
                                                    <ThumbsDown className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        )}

                                        <p suppressHydrationWarning className="text-[10px] opacity-40 text-right tabular-nums">
                                            {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </p>
                                        <button
                                            onClick={() => handleCopy(msg.id, msg.content)}
                                            className={clsx(
                                                "p-1.5 rounded-lg transition-all duration-200 opacity-0 group-hover:opacity-100 focus:opacity-100",
                                                msg.role === 'user'
                                                    ? "hover:bg-white/10 text-white/60 hover:text-white"
                                                    : "hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 hover:text-zinc-600 dark:text-zinc-500 dark:hover:text-zinc-300"
                                            )}
                                            aria-label="Copy message"
                                        >
                                            {copiedId === msg.id ? (
                                                <Check className="w-3.5 h-3.5" />
                                            ) : (
                                                <Copy className="w-3.5 h-3.5" />
                                            )}
                                        </button>
                                    </div>
                                )}
                            </div>

                            {/* User avatar — only on first in group */}
                            {msg.role === 'user' && (
                                <div className={clsx(
                                    "w-8 h-8 shrink-0",
                                    !isFirstInGroup ? "invisible" : "mt-0.5"
                                )}>
                                    {isFirstInGroup ? (
                                        <div className="w-8 h-8 rounded-xl bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center text-zinc-600 dark:text-zinc-400">
                                            <User className="w-4 h-4" />
                                        </div>
                                    ) : null}
                                </div>
                            )}
                        </div>
                    </React.Fragment>
                );
            })}

            {/* ── Typing indicator ── */}
            {isLoading && (
                <div className="flex gap-3 max-w-3xl mx-auto justify-start animate-message-enter mt-4">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white shrink-0 shadow-lg shadow-violet-500/25">
                        <Bot className="w-4 h-4" />
                    </div>
                    <div className="bg-white dark:bg-zinc-900 rounded-2xl rounded-bl-md px-4 py-3.5 border border-zinc-100 dark:border-zinc-800 shadow-sm">
                        <div className="flex items-center gap-1.5">
                            <div className="typing-dot" />
                            <div className="typing-dot" />
                            <div className="typing-dot" />
                        </div>
                    </div>
                </div>
            )}

            <div className="indicator-bottom" />
            <div ref={bottomSentinelRef} className="h-0 w-0 absolute bottom-0" />
            <div ref={bottomRef} />

            {/* ── Scroll to bottom button ── */}
            <div
                className={clsx(
                    "sticky bottom-4 flex justify-center z-30 pointer-events-none transition-all duration-300",
                    showScrollBtn ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2 pointer-events-none"
                )}
            >
                <button
                    onClick={scrollToBottom}
                    className="pointer-events-auto w-9 h-9 rounded-full bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 shadow-lg shadow-zinc-900/10 dark:shadow-black/30 flex items-center justify-center text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200 hover:shadow-xl transition-all duration-200"
                    aria-label="Scroll to bottom"
                >
                    <ArrowDown className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
}
