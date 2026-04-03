import { useState } from "react";
import { Sidebar, type PageId } from "@/components/Sidebar";
import { KnowledgePage } from "@/pages/KnowledgePage";
import { GraphPage } from "@/pages/GraphPage";
import { PracticePage } from "@/pages/PracticePage";
import { ExamPage } from "@/pages/ExamPage";
import { MistakesPage } from "@/pages/MistakesPage";
import { ToastProvider } from "@/components/ui/toast";

const PAGES: Record<PageId, React.ComponentType> = {
  knowledge: KnowledgePage,
  graph: GraphPage,
  practice: PracticePage,
  exam: ExamPage,
  mistakes: MistakesPage,
};

function App() {
  const [activePage, setActivePage] = useState<PageId>("knowledge");
  const ActiveComponent = PAGES[activePage];

  return (
    <ToastProvider>
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar active={activePage} onChange={setActivePage} />
        <main className="ml-[200px] flex-1 overflow-hidden">
          <ActiveComponent />
        </main>
      </div>
    </ToastProvider>
  );
}

export default App;