import { Persona } from './types';

export class AIResponseService {
    /**
     * Generates a response based on the message content and selected persona.
     * Calls the local Python backend.
     */
    static async generateResponse(message: string, persona: Persona): Promise<{ response: string, requestId?: string }> {
        try {
            const response = await fetch('http://127.0.0.1:8000/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message, persona }),
            });

            if (!response.ok) {
                throw new Error(`Backend error: ${response.statusText}`);
            }

            const data = await response.json();
            return { response: data.response, requestId: data.request_id };
        } catch (error) {
            console.error("Failed to connect to Python backend:", error);

            // Fallback if backend is down
            const fallbackResponse = persona === 'desi'
                ? "Arre yaar, server connect nahi ho raha. (Backend Offline)"
                : "Connection to server failed. Please ensure backend is running.";

            return { response: fallbackResponse };
        }
    }
}
