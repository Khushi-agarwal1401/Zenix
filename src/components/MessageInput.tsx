import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Sparkles, Mic, MicOff } from 'lucide-react';
import clsx from 'clsx';

interface SpeechRecognitionEvent {
    resultIndex: number;
    results: {
        length: number;
        [index: number]: {
            isFinal: boolean;
            [index: number]: {
                transcript: string;
            };
        };
    };
}

interface SpeechRecognitionErrorEvent {
    error: string;
}

interface ISpeechRecognition {
    continuous: boolean;
    interimResults: boolean;
    lang: string;
    maxAlternatives: number;
    start(): void;
    stop(): void;
    onstart: (() => void) | null;
    onresult: ((event: SpeechRecognitionEvent) => void) | null;
    onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
    onend: (() => void) | null;
}

declare global {
    interface Window {
        SpeechRecognition?: { new (): ISpeechRecognition };
        webkitSpeechRecognition?: { new (): ISpeechRecognition };
    }
}


// Supported Indian languages for speech recognition
const SPEECH_LANGUAGES = [
    { code: 'hi-IN', name: 'Hindi', short: 'हि' },
    { code: 'bn-IN', name: 'Bengali', short: 'বা' },
    { code: 'te-IN', name: 'Telugu', short: 'తె' },
    { code: 'mr-IN', name: 'Marathi', short: 'म' },
    { code: 'ta-IN', name: 'Tamil', short: 'த' },
    { code: 'gu-IN', name: 'Gujarati', short: 'ગુ' },
    { code: 'kn-IN', name: 'Kannada', short: 'ಕ' },
    { code: 'ml-IN', name: 'Malayalam', short: 'മ' },
    { code: 'pa-IN', name: 'Punjabi', short: 'ਪ' },
    { code: 'ur-IN', name: 'Urdu', short: 'اُ' },
    { code: 'en-IN', name: 'English', short: 'En' },
];

interface MessageInputProps {
    onSend: (message: string) => void;
    isLoading?: boolean;
}

export function MessageInput({ onSend, isLoading }: MessageInputProps) {
    const [input, setInput] = useState('');
    const [isRecording, setIsRecording] = useState(false);
    const [speechLanguage, setSpeechLanguage] = useState('hi-IN');
    const [showLangPicker, setShowLangPicker] = useState(false);
    const [speechSupported] = useState(() => {
        if (typeof window === 'undefined') return false;
        return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    });
    const [interimTranscript, setInterimTranscript] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const recognitionRef = useRef<ISpeechRecognition | null>(null);
    const langPickerRef = useRef<HTMLDivElement>(null);

    // Speech API support is checked during state initialization

    // Close language picker when clicking outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (langPickerRef.current && !langPickerRef.current.contains(e.target as Node)) {
                setShowLangPicker(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Auto-resize textarea
    useEffect(() => {
        const el = textareaRef.current;
        if (!el) return;
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 128) + 'px';
    }, [input]);

    const startRecording = useCallback(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert('Speech recognition is not supported in your browser. Please use Chrome or Edge.');
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = speechLanguage;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
            setIsRecording(true);
            setInterimTranscript('');
        };

        recognition.onresult = (event: SpeechRecognitionEvent) => {
            let interim = '';
            let final = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    final += transcript;
                } else {
                    interim += transcript;
                }
            }

            if (final) {
                setInput(prev => prev ? prev + ' ' + final : final);
                setInterimTranscript('');
            } else {
                setInterimTranscript(interim);
            }
        };

        recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
            console.error('Speech recognition error:', event.error);
            setIsRecording(false);
            setInterimTranscript('');
            if (event.error === 'not-allowed') {
                alert('Microphone access denied. Please allow microphone access in your browser settings.');
            }
        };

        recognition.onend = () => {
            setIsRecording(false);
            setInterimTranscript('');
        };

        recognitionRef.current = recognition;
        recognition.start();
    }, [speechLanguage]);

    const stopRecording = useCallback(() => {
        if (recognitionRef.current) {
            recognitionRef.current.stop();
            recognitionRef.current = null;
        }
        setIsRecording(false);
        setInterimTranscript('');
    }, []);

    const toggleRecording = () => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    const handleSend = () => {
        const textToSend = input.trim() || interimTranscript.trim();
        if (textToSend && !isLoading) {
            onSend(textToSend);
            setInput('');
            setInterimTranscript('');
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto';
            }
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const currentLang = SPEECH_LANGUAGES.find(l => l.code === speechLanguage) || SPEECH_LANGUAGES[0];
    const hasText = input.trim() || interimTranscript.trim();

    return (
        <div className="px-4 pb-4 pt-2 bg-white/90 dark:bg-zinc-950/90 backdrop-blur-2xl border-t border-zinc-200/50 dark:border-zinc-800/50 z-20 relative">
            <div className="max-w-3xl mx-auto relative">
                {/* Recording indicator */}
                {isRecording && (
                    <div className="absolute -top-12 left-0 right-0 flex items-center justify-center gap-2 animate-message-enter">
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800/50 rounded-full">
                            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                            <span className="text-xs font-medium text-red-600 dark:text-red-400">
                                {isRecording ? `Listening in ${currentLang.name}...` : 'Processing...'}
                            </span>
                            {interimTranscript && (
                                <span className="text-xs text-zinc-500 dark:text-zinc-400 max-w-[200px] truncate">
                                    &ldquo;{interimTranscript}&rdquo;
                                </span>
                            )}
                        </div>
                    </div>
                )}

                <div className="flex items-end gap-2 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm focus-within:ring-2 focus-within:ring-violet-500/20 focus-within:border-violet-400 dark:focus-within:border-violet-500 transition-all">
                    {/* Language picker */}
                    {speechSupported && (
                        <div className="relative pl-2 pb-2" ref={langPickerRef}>
                            <button
                                onClick={() => setShowLangPicker(!showLangPicker)}
                                className={clsx(
                                    "w-8 h-8 flex items-center justify-center rounded-lg transition-all duration-200",
                                    "text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300",
                                    "hover:bg-zinc-200/60 dark:hover:bg-zinc-800",
                                    showLangPicker && "bg-zinc-200/60 dark:bg-zinc-800 text-violet-500"
                                )}
                                aria-label="Select language"
                                title={`Speech language: ${currentLang.name}`}
                            >
                                <span className="text-[10px] font-bold">{currentLang.short}</span>
                            </button>

                            {showLangPicker && (
                                <div className="absolute bottom-full left-0 mb-2 w-40 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-lg overflow-hidden animate-message-enter z-50">
                                    {SPEECH_LANGUAGES.map(lang => (
                                        <button
                                            key={lang.code}
                                            onClick={() => {
                                                setSpeechLanguage(lang.code);
                                                setShowLangPicker(false);
                                            }}
                                            className={clsx(
                                                "w-full px-3 py-2 text-left text-sm flex items-center justify-between",
                                                "hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors",
                                                lang.code === speechLanguage
                                                    ? "bg-violet-50 dark:bg-violet-950/30 text-violet-600 dark:text-violet-400"
                                                    : "text-zinc-700 dark:text-zinc-300"
                                            )}
                                        >
                                            <span>{lang.name}</span>
                                            <span className="text-xs opacity-60">{lang.short}</span>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={
                            isLoading
                                ? "Zenix is thinking..."
                                : isRecording
                                ? `Listening in ${currentLang.name}...`
                                : "Ask Zenix anything..."
                        }
                        disabled={isLoading}
                        rows={1}
                        className="flex-1 px-4 py-3 bg-transparent focus:outline-none placeholder:text-zinc-400 dark:placeholder:text-zinc-500 text-[15px] leading-relaxed resize-none min-h-[2.5rem] max-h-[8rem] disabled:opacity-50"
                    />

                    <div className="flex items-center gap-1.5 pb-2 pr-2">
                        {/* Microphone button */}
                        {speechSupported && (
                            <button
                                onClick={toggleRecording}
                                disabled={isLoading}
                                className={clsx(
                                    "w-9 h-9 flex items-center justify-center rounded-xl transition-all duration-200",
                                    isRecording
                                        ? "bg-red-500 text-white shadow-lg shadow-red-500/30 animate-pulse"
                                        : "text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 hover:bg-zinc-200/60 dark:hover:bg-zinc-800",
                                    isLoading && "opacity-50 cursor-not-allowed"
                                )}
                                aria-label={isRecording ? "Stop recording" : "Start voice input"}
                                title={isRecording ? "Stop recording" : `Voice input (${currentLang.name})`}
                            >
                                {isRecording ? (
                                    <MicOff className="w-4 h-4" />
                                ) : (
                                    <Mic className="w-4 h-4" />
                                )}
                            </button>
                        )}

                        {/* Send button */}
                        {isLoading ? (
                            <div className="w-9 h-9 flex items-center justify-center">
                                <Sparkles className="w-4 h-4 text-violet-500 animate-spin" />
                            </div>
                        ) : (
                            <button
                                onClick={handleSend}
                                disabled={!hasText}
                                className={clsx(
                                    "w-9 h-9 flex items-center justify-center rounded-xl transition-all duration-200",
                                    hasText
                                        ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 hover:shadow-md hover:shadow-zinc-900/10 dark:hover:shadow-zinc-100/10 active:scale-95"
                                        : "bg-zinc-200/60 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-600 cursor-not-allowed"
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
                    {speechSupported
                        ? "🎤 Tap mic to speak in Hindi, Bengali, Tamil, and 8+ Indian languages"
                        : "Zenix can make mistakes. Check important info."
                    }
                </p>
            </div>
        </div>
    );
}
