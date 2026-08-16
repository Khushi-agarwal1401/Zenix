import clsx from 'clsx';
import { Briefcase, Coffee } from 'lucide-react';
import { Persona } from '@/lib/types';

interface PersonaToggleProps {
    currentPersona: Persona;
    onToggle: (persona: Persona) => void;
}

export function PersonaToggle({ currentPersona, onToggle }: PersonaToggleProps) {
    return (
        <div className="flex bg-zinc-100 dark:bg-zinc-800 p-1 rounded-full border border-zinc-200 dark:border-zinc-700 w-fit">
            <button
                onClick={() => onToggle('desi')}
                className={clsx(
                    "flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200",
                    currentPersona === 'desi'
                        ? "bg-amber-100 text-amber-900 shadow-sm ring-1 ring-amber-200"
                        : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
                )}
            >
                <Coffee className="w-4 h-4" />
                Desi
            </button>
            <button
                onClick={() => onToggle('sarkari')}
                className={clsx(
                    "flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200",
                    currentPersona === 'sarkari'
                        ? "bg-blue-100 text-blue-900 shadow-sm ring-1 ring-blue-200"
                        : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
                )}
            >
                <Briefcase className="w-4 h-4" />
                Sarkari
            </button>
        </div>
    );
}
