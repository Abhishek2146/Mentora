export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-white border-t border-gray-200 py-4 px-6">
      <div className="flex items-center justify-between text-sm text-gray-500">
        <span>&copy; {currentYear} Mentora AI Learning Companion</span>
        <div className="flex items-center space-x-4">
          <span>Version 1.0.0</span>
          <span>•</span>
          <span>Powered by AI</span>
        </div>
      </div>
    </footer>
  );
}
