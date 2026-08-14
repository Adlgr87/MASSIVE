import { Routes, Route } from 'react-router-dom';
import { Button } from '@/components/ui/button';

function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold">MASSIVE UIL</h1>
        </div>
      </header>
      <main className="container mx-auto px-4 py-8">
        <Routes>
          <Route
            path="/"
            element={
              <div className="space-y-4">
                <h2 className="text-xl font-semibold">Welcome</h2>
                <p className="text-muted-foreground">
                  MASSIVE UIL frontend is ready.
                </p>
                <Button variant="default">Get Started</Button>
              </div>
            }
          />
        </Routes>
      </main>
    </div>
  );
}

export default App;
