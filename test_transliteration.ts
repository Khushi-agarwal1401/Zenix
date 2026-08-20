import { transliterateToDevanagari, transliterateToBengali, transliterateToGujarati, transliterateToTamil, transliterateToTelugu, transliterateToGurmukhi } from './src/lib/language_engine.ts';

console.log('Devanagari:', transliterateToDevanagari('namaste kya haal hai'));
console.log('Bengali:', transliterateToBengali('namaskar kemon acho'));
console.log('Gujarati:', transliterateToGujarati('namaste kem cho'));
console.log('Tamil:', transliterateToTamil('vanakkam epdi irukku'));
console.log('Telugu:', transliterateToTelugu('namaskaram ela unnavu'));
console.log('Gurmukhi:', transliterateToGurmukhi('sat sri akal ki haal hai'));