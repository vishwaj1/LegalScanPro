'use client'
import { Shield } from "lucide-react";
import Link from "next/link";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-[#f9fafb]">
      {/* Header */}
      <header className="bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-[#0f172a]" />
              <span className="ml-2 text-xl font-bold text-[#0f172a]">LegalScanPro</span>
            </div>
            <nav className="flex space-x-4">
              <Link href="/" className="text-gray-600 hover:text-gray-900">Home</Link>
              <Link href="#" className="text-gray-600 hover:text-gray-900">Features</Link>
              <Link href="#" className="text-gray-600 hover:text-gray-900">Pricing</Link>
              <Link href="#" className="text-gray-600 hover:text-gray-900">Contact</Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-grow">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="col-span-2">
              <div className="flex items-center">
                <Shield className="h-6 w-6 text-[#0f172a]" />
                <span className="ml-2 text-lg font-bold text-[#0f172a]">LegalScanPro</span>
              </div>
              <p className="mt-2 text-sm text-gray-500">
                AI-powered legal document analysis for startups and businesses.
              </p>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Product</h3>
              <ul className="mt-4 space-y-2">
                <li><Link href="#" className="text-sm text-gray-500 hover:text-gray-900">Features</Link></li>
                <li><Link href="#" className="text-sm text-gray-500 hover:text-gray-900">Pricing</Link></li>
                <li><Link href="#" className="text-sm text-gray-500 hover:text-gray-900">Security</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Company</h3>
              <ul className="mt-4 space-y-2">
                <li><Link href="#" className="text-sm text-gray-500 hover:text-gray-900">About</Link></li>
                <li><Link href="#" className="text-sm text-gray-500 hover:text-gray-900">Contact</Link></li>
                <li><Link href="#" className="text-sm text-gray-500 hover:text-gray-900">Privacy</Link></li>
              </ul>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t border-gray-100">
            <p className="text-sm text-gray-500 text-center">
              © 2025 LegalScanPro. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
} 