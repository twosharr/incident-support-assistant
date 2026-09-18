import { StatusSidebar } from "./components/StatusSidebar";
import { ChatWindow } from "./components/ChatWindow";

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden bg-teams-bg">
      {/* Left sidebar: service status panel */}
      <StatusSidebar />

      {/* Main chat area */}
      <div className="flex-1 min-w-0">
        <ChatWindow />
      </div>
    </div>
  );
}
