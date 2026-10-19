"use client";
export default function ErrorState({ reset }: { reset: () => void }) { return <main className="container section"><h1>Staff console unavailable / عملے کا کنسول دستیاب نہیں</h1><p role="alert">Please try again. / دوبارہ کوشش کریں۔</p><button className="button" onClick={reset}>Try again / دوبارہ کوشش کریں</button></main>; }
