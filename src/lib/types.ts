export type Persona = 'sarkari' | 'desi';

export interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    persona?: Persona; // The persona active when this message was generated
    requestId?: string; // For feedback tracking
}
