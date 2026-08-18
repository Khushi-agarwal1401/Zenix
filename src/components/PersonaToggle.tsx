import clsx from 'clsx';
import { Briefcase, Coffee } from 'lucide-react';
import { Persona } from '@/lib/types';

interface PersonaToggleProps {
    currentPersona: Persona;
    onToggle: (persona: Persona) => void;
}

export function PersonaToggle({ currentPersona, onToggle }: PersonaToggleProps) {
    return (
        <div className="flex bg-zinc-100/80 dark:bg-zinc-800/80 p-1 rounded-xl border border-zinc-200/50 dark:border-zinc-700/50 w-fit">
            <button
                onClick={() => onToggle('desi')}
                className={clsx(
                    "flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all duration-200",
                    currentPersona === 'desi'
                        ? "bg-amber-100 text-amber-800 shadow-sm dark:bg-amber-950/40 dark:text-amber-200 dark:shadow-amber-900/20"
                        : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-700/50"
                )}
                aria-pressed={currentPersona === 'desi'}
            >
                <Coffee className="w-3.5 h-3.5" />
                Desi
            </button>
            <button
                onClick={() => onToggle('sarkari')}
                className={clsx(
                    "flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all duration-200",
                    currentPersona === 'sarkari'
                        ? "bg-sky-100 text-sky-800 shadow-sm dark:bg-sky-950/40 dark:text-sky-200 dark:shadow-sky-900/20"
                        : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-700/50"
                )}
                aria-pressed={currentPersona === 'sarkari'}
            >
                <Briefcase className="w-3.5 h-3.5" />
                Sarkari
            </button>
        </div>
    );
}
