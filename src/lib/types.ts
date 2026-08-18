export type Persona = 'sarkari' | 'desi';

export interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    persona?: Persona;
    requestId?: string;
    isError?: boolean;
}
