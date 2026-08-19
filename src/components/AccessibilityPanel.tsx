"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Settings, Eye, Type, Volume2, X, Sun, Moon, ZoomIn, ZoomOut } from "lucide-react";
import clsx from "clsx";

interface AccessibilitySettings {
    highContrast: boolean;
    fontSize: number; // percentage: 80, 100, 120, 140, 160
    reduceMotion: boolean;
    screenReaderAnnouncements: boolean;
    dyslexiaFont: boolean;
    lineSpacing: number; // 1.0, 1.5, 2.0
}

const DEFAULT_SETTINGS: AccessibilitySettings = {
    highContrast: false,
    fontSize: 100,
    reduceMotion: false,
    screenReaderAnnouncements: true,
    dyslexiaFont: false,
    lineSpacing: 1.5,
};

const FONT_SIZES = [80, 100, 120, 140, 160];
const LINE_SPACINGS = [1.0, 1.5, 2.0];

export function AccessibilityPanel() {
    const [isOpen, setIsOpen] = useState(false);
    const [settings, setSettings] = useState<AccessibilitySettings>(DEFAULT_SETTINGS);

    // Load settings from localStorage
    useEffect(() => {
        try {
            const saved = localStorage.getItem("zenix-accessibility");
            if (saved) {
                setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(saved) });
            }
        } catch {}
    }, []);

    // Apply settings to document
    useEffect(() => {
        const root = document.documentElement;

        // Font size
        root.style.setProperty("--accessibility-font-scale", `${settings.fontSize / 100}`);

        // High contrast
        if (settings.highContrast) {
            root.classList.add("high-contrast");
        } else {
            root.classList.remove("high-contrast");
        }

        // Reduce motion
        if (settings.reduceMotion) {
            root.classList.add("reduce-motion");
        } else {
            root.classList.remove("reduce-motion");
        }

        // Dyslexia font
        if (settings.dyslexiaFont) {
            root.classList.add("dyslexia-font");
        } else {
            root.classList.remove("dyslexia-font");
        }

        // Line spacing
        root.style.setProperty("--accessibility-line-spacing", String(settings.lineSpacing));

        // Save to localStorage
        try {
            localStorage.setItem("zenix-accessibility", JSON.stringify(settings));
        } catch {}
    }, [settings]);

    // Screen reader announcements
    const announce = useCallback((text: string) => {
        if (!settings.screenReaderAnnouncements) return;
        const el = document.getElementById("sr-announcer");
        if (el) {
            el.textContent = text;
            setTimeout(() => { el.textContent = ""; }, 1000);
        }
    }, [settings.screenReaderAnnouncements]);

    const updateSetting = <K extends keyof AccessibilitySettings>(
        key: K,
        value: AccessibilitySettings[K]
    ) => {
        setSettings((prev) => ({ ...prev, [key]: value }));
        announce(`${key.replace(/([A-Z])/g, " $1").trim()} set to ${value}`);
    };

    const resetSettings = () => {
        setSettings(DEFAULT_SETTINGS);
        announce("Accessibility settings reset to defaults");
    };

    return (
        <>
            {/* Screen reader announcer (invisible) */}
            <div
                id="sr-announcer"
                role="status"
                aria-live="polite"
                aria-atomic="true"
                className="sr-only"
            />

            {/* Toggle button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={clsx(
                    "fixed bottom-20 right-4 z-50 w-10 h-10 rounded-full",
                    "flex items-center justify-center transition-all duration-200",
                    "shadow-lg hover:shadow-xl active:scale-95",
                    isOpen
                        ? "bg-zinc-800 text-white dark:bg-zinc-200 dark:text-zinc-900"
                        : "bg-white dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700"
                )}
                aria-label="Accessibility settings"
                title="Accessibility settings"
            >
                <Eye className="w-5 h-5" />
            </button>

            {/* Settings panel */}
            {isOpen && (
                <div className="fixed bottom-32 right-4 z-50 w-80 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl overflow-hidden animate-message-enter">
                    {/* Header */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
                        <h3 className="font-semibold text-sm flex items-center gap-2">
                            <Eye className="w-4 h-4" />
                            Accessibility
                        </h3>
                        <button
                            onClick={() => setIsOpen(false)}
                            className="p-1 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800"
                            aria-label="Close"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>

                    <div className="p-4 space-y-5 max-h-[60vh] overflow-y-auto">
                        {/* Font Size */}
                        <div>
                            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-2 block">
                                Text Size
                            </label>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => updateSetting("fontSize", Math.max(80, settings.fontSize - 20))}
                                    disabled={settings.fontSize <= 80}
                                    className="p-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 disabled:opacity-30"
                                    aria-label="Decrease font size"
                                >
                                    <ZoomOut className="w-4 h-4" />
                                </button>
                                <div className="flex-1 flex gap-1">
                                    {FONT_SIZES.map((size) => (
                                        <button
                                            key={size}
                                            onClick={() => updateSetting("fontSize", size)}
                                            className={clsx(
                                                "flex-1 py-1.5 rounded-lg text-xs font-medium transition-all",
                                                settings.fontSize === size
                                                    ? "bg-violet-600 text-white"
                                                    : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700"
                                            )}
                                        >
                                            {size}%
                                        </button>
                                    ))}
                                </div>
                                <button
                                    onClick={() => updateSetting("fontSize", Math.min(160, settings.fontSize + 20))}
                                    disabled={settings.fontSize >= 160}
                                    className="p-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 disabled:opacity-30"
                                    aria-label="Increase font size"
                                >
                                    <ZoomIn className="w-4 h-4" />
                                </button>
                            </div>
                        </div>

                        {/* Line Spacing */}
                        <div>
                            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-2 block">
                                Line Spacing
                            </label>
                            <div className="flex gap-1">
                                {LINE_SPACINGS.map((spacing) => (
                                    <button
                                        key={spacing}
                                        onClick={() => updateSetting("lineSpacing", spacing)}
                                        className={clsx(
                                            "flex-1 py-1.5 rounded-lg text-xs font-medium transition-all",
                                            settings.lineSpacing === spacing
                                                ? "bg-violet-600 text-white"
                                                : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400"
                                        )}
                                    >
                                        {spacing}x
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Toggle options */}
                        <div className="space-y-3">
                            <ToggleRow
                                label="High Contrast"
                                description="Increase contrast for better visibility"
                                icon={<Sun className="w-4 h-4" />}
                                enabled={settings.highContrast}
                                onChange={(v) => updateSetting("highContrast", v)}
                            />
                            <ToggleRow
                                label="Reduce Motion"
                                description="Minimize animations"
                                icon={<Settings className="w-4 h-4" />}
                                enabled={settings.reduceMotion}
                                onChange={(v) => updateSetting("reduceMotion", v)}
                            />
                            <ToggleRow
                                label="Dyslexia-Friendly Font"
                                description="Use OpenDyslexic font"
                                icon={<Type className="w-4 h-4" />}
                                enabled={settings.dyslexiaFont}
                                onChange={(v) => updateSetting("dyslexiaFont", v)}
                            />
                            <ToggleRow
                                label="Screen Reader Hints"
                                description="Extra announcements for screen readers"
                                icon={<Volume2 className="w-4 h-4" />}
                                enabled={settings.screenReaderAnnouncements}
                                onChange={(v) => updateSetting("screenReaderAnnouncements", v)}
                            />
                        </div>

                        {/* Reset */}
                        <button
                            onClick={resetSettings}
                            className="w-full py-2 text-xs text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 border border-zinc-200 dark:border-zinc-700 rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
                        >
                            Reset to Defaults
                        </button>
                    </div>
                </div>
            )}
        </>
    );
}

function ToggleRow({
    label,
    description,
    icon,
    enabled,
    onChange,
}: {
    label: string;
    description: string;
    icon: React.ReactNode;
    enabled: boolean;
    onChange: (v: boolean) => void;
}) {
    return (
        <button
            onClick={() => onChange(!enabled)}
            className={clsx(
                "w-full flex items-center gap-3 p-2.5 rounded-xl transition-all",
                "border text-left",
                enabled
                    ? "bg-violet-50 dark:bg-violet-950/30 border-violet-200 dark:border-violet-800/50"
                    : "bg-zinc-50 dark:bg-zinc-800/50 border-zinc-200 dark:border-zinc-700/50"
            )}
            role="switch"
            aria-checked={enabled}
        >
            <div className={clsx(
                "p-1.5 rounded-lg",
                enabled ? "bg-violet-100 dark:bg-violet-900/50 text-violet-600 dark:text-violet-400" : "bg-zinc-100 dark:bg-zinc-700 text-zinc-500"
            )}>
                {icon}
            </div>
            <div className="flex-1 min-w-0">
                <div className="text-xs font-medium">{label}</div>
                <div className="text-[10px] text-zinc-500 dark:text-zinc-400 truncate">{description}</div>
            </div>
            <div className={clsx(
                "w-9 h-5 rounded-full transition-all relative",
                enabled ? "bg-violet-600" : "bg-zinc-300 dark:bg-zinc-600"
            )}>
                <div className={clsx(
                    "absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all",
                    enabled ? "left-[18px]" : "left-0.5"
                )} />
            </div>
        </button>
    );
}
