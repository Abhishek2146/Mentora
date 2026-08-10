import DashboardLayout from "@/components/layout/DashboardLayout";
import apiClient from "@/lib/api";
import { useEffect, useState, useRef } from "react";
import { Flashcard, FlashcardDeck } from "@/types";

export default function FlashcardsPage() {
  const [decks, setDecks] = useState<FlashcardDeck[]>([]);
  const [selectedDeck, setSelectedDeck] = useState<FlashcardDeck | null>(null);
  const [currentCard, setCurrentCard] = useState<Flashcard | null>(null);
  const [isFlipped, setIsFlipped] = useState(false);
  const [cardIndex, setCardIndex] = useState(0);

  useEffect(() => {
    fetchDecks();
  }, []);

  const fetchDecks = async () => {
    try {
      const response = await apiClient.get("/api/v1/flashcards/");
      setDecks(response.data);
    } catch (error) {
      console.error("Failed to fetch decks:", error);
    }
  };

  const startReview = (deck: FlashcardDeck) => {
    setSelectedDeck(deck);
    setCardIndex(0);
    setCurrentCard(deck.flashcards[0]);
    setIsFlipped(false);
  };

  const nextCard = () => {
    if (!selectedDeck || cardIndex >= selectedDeck.flashcards.length - 1) {
      alert("Session complete!");
      setSelectedDeck(null);
      return;
    }
    setCardIndex(cardIndex + 1);
    setCurrentCard(selectedDeck.flashcards[cardIndex + 1]);
    setIsFlipped(false);
  };

  const prevCard = () => {
    if (cardIndex > 0) {
      setCardIndex(cardIndex - 1);
      setCurrentCard(selectedDeck!.flashcards[cardIndex - 1]);
      setIsFlipped(false);
    }
  };

  if (!selectedDeck) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-900">Flashcards</h1>
            <button className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700">
              + New Deck
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {decks.map((deck) => (
              <div key={deck.id} className="bg-white rounded-lg shadow p-6 cursor-pointer hover:shadow-md" onClick={() => startReview(deck)}>
                <h3 className="font-bold text-lg">{deck.title}</h3>
                <p className="text-gray-600 mt-1 text-sm">{deck.flashcards.length} cards</p>
              </div>
            ))}
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-2xl mx-auto">
        <div className="mb-4 flex justify-between items-center">
          <h2 className="text-xl font-bold">{selectedDeck.title}</h2>
          <button onClick={() => setSelectedDeck(null)} className="text-gray-500 hover:text-gray-700">
            ← Back
          </button>
        </div>

        {currentCard && (
          <div
            className="bg-white rounded-xl shadow-xl p-8 h-80 flex flex-col justify-center items-center cursor-pointer"
            onClick={() => setIsFlipped(!isFlipped)}
          >
            {!isFlipped ? (
              <>
                <h3 className="text-2xl font-bold text-center mb-4">Front</h3>
                <p className="text-lg text-center">{currentCard.front}</p>
              </>
            ) : (
              <>
                <h3 className="text-2xl font-bold text-center mb-4">Back</h3>
                <p className="text-lg text-center">{currentCard.back}</p>
              </>
            )}
          </div>
        )}

        <div className="flex justify-center space-x-4 mt-6">
          <button onClick={prevCard} className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">
            Previous
          </button>
          <div className="px-4 py-2 text-sm text-gray-600">
            Card {cardIndex + 1} of {selectedDeck.flashcards.length}
          </div>
          <button onClick={nextCard} className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">
            Next
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
}
