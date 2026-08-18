import { Persona, Message } from './types';

// Persistent session ID for conversation continuity across requests
let _sessionId: string | null = null;

function getSessionId(): string {
    if (!_sessionId) {
        _sessionId = crypto.randomUUID();
    }
    return _sessionId;
}

/** Reset session (e.g., when user starts a new chat) */
export function resetSession(): void {
    _sessionId = null;
}

export class AIResponseService {
    /**
     * Generates a response based on the message content and selected persona.
     * Calls the local Python backend with session-based conversation history.
     */
    static async generateResponse(message: string, persona: Persona, history?: Message[]): Promise<{ response: string, requestId?: string }> {
        const lowerMessage = message.toLowerCase().trim();

        // Check if this is a reply to the chai question
        if (history && history.length > 0) {
            const lastMsg = history[history.length - 1];
            if (lastMsg.role === 'assistant' && lastMsg.content.includes("Chai ka time hai kya")) {
                const yesPhrases = ["haan", "ha", "yes", "yup", "haan bhai", "ha bhai", "ji haan", "yes please", "sure", "ok", "okay"];
                const noPhrases = ["nahi", "na", "no", "nope", "nahi yaar", "na bhai", "not now"];
                if (yesPhrases.some(phrase => lowerMessage.includes(phrase))) {
                    return {
                        response: persona === 'desi'
                            ? "Badiya! Ek mast kadak adrak wali chai ho jaye. Aur batao aur kya madad karun?"
                            : "Excellent! Let's take a quick tea break. How else can I assist you?"
                    };
                }
                if (noPhrases.some(phrase => lowerMessage.includes(phrase))) {
                    return {
                        response: persona === 'desi'
                            ? "Arre koi baat nahi. Bina chai ke hi kaam chalate hain. Aur batao kya chal raha hai?"
                            : "No problem. Let's continue. What's on your mind?"
                    };
                }
            }
        }

        
        // Intercept well-being phrases
        const wellbeingPhrases = ["i am good", "i'm good", "im good", "doing well", "i am fine", "i'm fine", "im fine", "all good", "doing good"];
        if (wellbeingPhrases.some(phrase => lowerMessage.includes(phrase))) {
            return {
                response: persona === 'desi'
                    ? "Badhiya yaar! Aur batao, kya chal raha hai aaj kal?"
                    : "That's great to hear! How can I assist you further today?"
            };
        }

        // Intercept boredom phrases
        const boredPhrases = ["nothing just feeling boring", "feeling bored", "getting bored", "i am bored", "so boring", "bore ho raha hu", "bore ho rahi hu", "boring lag raha hai"];
        if (boredPhrases.some(phrase => lowerMessage.includes(phrase))) {
            return {
                response: persona === 'desi'
                    ? "Arre bore ho rahe ho? Chalo koi mast joke sunata hu ya phir koi interesting topic pe baat karte hain! Kya discuss karna hai?"
                    : "I understand you're feeling bored. We could play a word game, learn something new, or I can tell you some interesting facts. What would you prefer?"
            };
        }

        // Intercept joke requests
        const jokePhrases = ["joke sunao", "tell me a joke", "make me laugh", "koi joke suna", "joke batao", "chutkula sunao"];
        if (jokePhrases.some(phrase => lowerMessage.includes(phrase))) {
            const desiJokes = [
                "Teacher: Pappu, batao 'I am beautiful' kaun sa tense hai?\nPappu: Past tense, madam!\nTeacher: Kyun?\nPappu: Kyunki ab aapke chehre pe jhuriya aa gayi hain! 😂",
                "Ek dost: Bhai, shaadi ke baad kitna badal gaya tu!\nDusra dost: Arre, abhi toh main badla bhi nahi hoon. Ye toh trailer hai, main picture baaki hai mere dost! 😜",
                "Pati: Aaj khane me kya hai?\nPatni: Zeher!\nPati: Chalo theek hai, main kha ke sota hoon, tum thoda late khana warna dono eksath jayenge toh bacho ka kya hoga! 😂",
                "Boss: Kahan the itni der se?\nEmployee: Sir, traffic jam mein phans gaya tha.\nBoss: Toh nikal kyu nahi gaye?\nEmployee: Kyunki main gadi mein tha, toothpaste mein nahi! 🚗😆",
                "Santa: Bhai kal maine ek macchar ko bina mare bhaga diya.\nBanta: Kaise?\nSanta: Main chupke se gaya aur uske kaan me bola 'Bhag ja meri patni aa rahi hai!' 🦟😂",
                "Doctor: Aapka vajan kaise badh gaya?\nMareez: Roz dawai khata hoon na isliye.\nDoctor: Kaunsi dawai?\nMareez: Arre wahi jo aapne likh ke di thi - 'Khane ke baad khani hai'! Toh main khane ke baad dusra khana khata hoon! 🍔🤣",
                "Baap: Beta, agar tum is baar fail huye to mujhe papa mat kehna.\nResult aane par Baap: Kaisa raha result?\nBeta: Sorry Ramesh, main fail ho gaya! 😂",
                "Teacher: Class me shanti kyu hai?\nStudent: Kyunki aaj Shanti absent hai! 🤣",
                "Doctor: Tumhe aisi bimari hai jisme insaan ko lagta hai ki uski patni hamesha sahi hoti hai.\nMareez: Par doctor, meri patni toh hamesha sach mein sahi hoti hai!\nDoctor: Dekha, bimari kitni purani ho chuki hai! 😅",
                "Judge: Tumne dukaandaar ko dande se kyu maara?\nChor: Kyunki board pe likha tha, 'Bhaari chhoot', isliye main lath maarne chala gaya! 🏏😂",
                "Girlfriend: Jaan, main tumhare bina mar jaungi.\nBoyfriend: Thik hai, main kal aata hu, mujhe aaj IPL final dekhna hai! 🏏😝",
                "Biwi: Main maike ja rahi hu.\nPati: Thik hai.\nBiwi: Kuch kehna hai?\nPati: Nahi.\nBiwi: Toh andar hi andar itni zor se khushi se naach kyu rahe ho! 🕺😂"
            ];
            
            const englishJokes = [
                "Why don't scientists trust atoms? Because they make up everything! 😄",
                "Why did the scarecrow win an award? Because he was outstanding in his field! 🌾",
                "What do you call a fake noodle? An impasta! 🍝",
                "Why couldn't the bicycle stand up by itself? It was two tired. 🚲😴",
                "What do you call a bear with no teeth? A gummy bear! 🐻🍬",
                "Why did the math book look sad? Because it had too many problems. 📘😢",
                "How does a penguin build its house? Igloos it together! 🐧🧊",
                "Why did the tomato turn red? Because it saw the salad dressing! 🍅😳",
                "What do you get when you cross a snowman and a vampire? Frostbite. ⛄🧛",
                "Why do seagulls fly over the ocean? Because if they flew over the bay, we'd call them bagels. 🌊🐦",
                "What do you call a sleeping dinosaur? A dino-snore! 🦖💤",
                "Why did the computer go to the doctor? Because it had a virus! 💻🤒",
                "Why are ghosts bad at lying? Because you can see right through them! 👻👀",
                "What do you call cheese that isn't yours? Nacho cheese! 🧀😂"
            ];

            const jokes = persona === 'desi' ? desiJokes : englishJokes;
            const randomJoke = jokes[Math.floor(Math.random() * jokes.length)];

            return { response: randomJoke };
        }

        try {
            const response = await fetch('http://127.0.0.1:8000/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message,
                    persona,
                    session_id: getSessionId(),
                }),
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

    /**
     * Streaming version of generateResponse.
     * Calls the SSE /chat/stream endpoint and yields token chunks.
     * Falls back to non-streaming if the streaming endpoint fails.
     */
    static async *generateStreamingResponse(
        message: string,
        persona: Persona,
        history?: Message[],
    ): AsyncGenerator<{ token: string; done: boolean; requestId?: string; fullResponse?: string }, void> {
        // Check interceptors first (same as non-streaming)
        const lowerMessage = message.toLowerCase().trim();

        if (history && history.length > 0) {
            const lastMsg = history[history.length - 1];
            if (lastMsg.role === 'assistant' && lastMsg.content.includes("Chai ka time hai kya")) {
                const yesPhrases = ["haan", "ha", "yes", "yup", "ok", "okay"];
                const noPhrases = ["nahi", "na", "no", "nope", "not now"];
                if (yesPhrases.some(p => lowerMessage.includes(p))) {
                    yield { token: persona === 'desi'
                        ? "Badiya! Ek mast kadak adrak wali chai ho jaye. Aur batao aur kya madad karun?"
                        : "Excellent! Let's take a quick tea break. How else can I assist you?",
                        done: true };
                    return;
                }
                if (noPhrases.some(p => lowerMessage.includes(p))) {
                    yield { token: persona === 'desi'
                        ? "Arre koi baat nahi. Bina chai ke hi kaam chalate hain. Aur batao kya chal raha hai?"
                        : "No problem. Let's continue. What's on your mind?",
                        done: true };
                    return;
                }
            }
        }

        const wellbeingPhrases = ["i am good", "i'm good", "doing well", "i am fine", "i'm fine", "all good"];
        if (wellbeingPhrases.some(p => lowerMessage.includes(p))) {
            yield { token: persona === 'desi'
                ? "Badhiya yaar! Aur batao, kya chal raha hai aaj kal?"
                : "That's great to hear! How can I assist you further today?",
                done: true };
            return;
        }

        const boredPhrases = ["feeling bored", "getting bored", "i am bored", "so boring"];
        if (boredPhrases.some(p => lowerMessage.includes(p))) {
            yield { token: persona === 'desi'
                ? "Arre bore ho rahe ho? Chalo koi mast joke sunata hu ya phir koi interesting topic pe baat karte hain! Kya discuss karna hai?"
                : "I understand you're feeling bored. We could play a word game, learn something new, or I can tell you some interesting facts.",
                done: true };
            return;
        }

        const jokePhrases = ["joke sunao", "tell me a joke", "make me laugh", "joke batao", "chutkula sunao"];
        if (jokePhrases.some(p => lowerMessage.includes(p))) {
            const desiJokes = [
                "Teacher: Pappu, batao 'I am beautiful' kaun sa tense hai?\nPappu: Past tense, madam! 😂",
                "Ek dost: Bhai, shaadi ke baad kitna badal gaya tu!\nDusra dost: Ye toh trailer hai, main picture baaki hai mere dost! 😜",
                "Boss: Kahan the itni der se?\nEmployee: Sir, traffic jam mein phans gaya tha.\nBoss: Toh nikal kyu nahi gaye?\nEmployee: Kyunki main gadi mein tha, toothpaste mein nahi! 🚗😆",
            ];
            const englishJokes = [
                "Why don't scientists trust atoms? Because they make up everything! 😄",
                "Why did the scarecrow win an award? Because he was outstanding in his field! 🌾",
                "What do you call a fake noodle? An impasta! 🍝",
            ];
            const jokes = persona === 'desi' ? desiJokes : englishJokes;
            yield { token: jokes[Math.floor(Math.random() * jokes.length)], done: true };
            return;
        }

        // Streaming SSE call
        try {
            const response = await fetch('http://127.0.0.1:8000/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, persona, session_id: getSessionId() }),
            });

            if (!response.ok) throw new Error(`Backend error: ${response.statusText}`);

            const reader = response.body?.getReader();
            if (!reader) throw new Error('No response body');

            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.type === 'token') {
                            yield { token: data.content, done: false };
                        } else if (data.type === 'done') {
                            yield {
                                token: '',
                                done: true,
                                requestId: data.request_id,
                                fullResponse: data.full_response,
                            };
                        }
                    } catch {}
                }
            }
        } catch (error) {
            console.error("Streaming failed, falling back to non-streaming:", error);
            // Fallback to non-streaming
            const result = await this.generateResponse(message, persona, history);
            yield { token: result.response, done: true, requestId: result.requestId };
        }
    }
}
