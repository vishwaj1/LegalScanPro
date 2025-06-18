'use client'
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Unlock } from "lucide-react";
//import { Unlock, FileText, Shield, ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import Layout from "@/components/layout";

export default function PreviewPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [previewData, setPreviewData] = useState<{
    issues: { severe: number; important: number; minor: number };
    examples: { type: string; detail: string }[];
  } | null>(null);
  const [unlocked, setUnlocked] = useState(false);

  const router = useRouter();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", selectedFile);
    try {
      const res = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });
      console.log(res);
      //const data = await res.json();
      setPreviewData({
        issues: {
          severe: 3,
          important: 5,
          minor: 8,
        },
        examples: [
          { type: "Severe", detail: "Missing signature on SAFE note" },
          { type: "Important", detail: "Inconsistent cap table vs. founder agreement" },
        ],
      });
    } catch (error) {
      console.error("Upload failed", error);
    } finally {
      setUploading(false);
    }
  };

  const handleUnlock = () => {
    setUnlocked(true);
    router.push("/payment");
  };

  return (
    <Layout>
      <div className="py-16 px-4">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white shadow-xl rounded-3xl p-10 border border-gray-100">
            <h1 className="text-3xl font-bold text-black text-center mb-6">Upload Legal Documents</h1>
            <div className="flex flex-col items-center gap-4">
              <input
                type="file"
                onChange={handleFileChange}
                accept=".pdf,.doc,.docx,.zip"
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-[#f3f4f6] hover:file:bg-[#e5e7eb]"
              />
              <p className="text-sm text-gray-500 mt-1">Supported formats: PDF, DOC, DOCX, ZIP</p>
              <Button 
                onClick={handleUpload} 
                disabled={uploading || !selectedFile} 
                className="w-full bg-black font-bold hover:bg-gray-800 text-white transition-colors duration-200"
              >
                {uploading ? "Uploading..." : "Upload Document"}
              </Button>
            </div>
          </div>

          {previewData && (
            <div className="mt-10 bg-white shadow-xl rounded-3xl p-8 border border-gray-100">
              <h2 className="text-2xl font-semibold text-black mb-4 text-center">Preview (Freemium)</h2>
              <div className="grid grid-cols-3 gap-4 text-center mb-4">
                <div>
                  <p className="text-sm text-gray-500">Severe</p>
                  <p className="text-xl font-bold text-red-600">{previewData.issues.severe}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Important</p>
                  <p className="text-xl font-bold text-yellow-600">{previewData.issues.important}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Minor</p>
                  <p className="text-xl font-bold text-green-600">{previewData.issues.minor}</p>
                </div>
              </div>
              <h3 className="text-md text-black font-medium mb-2">Examples:</h3>
              <ul className="list-disc ml-5 text-sm text-gray-700">
                {previewData.examples.map((ex, idx) => (
                  <li key={idx} className="mb-1">{ex.type}: {ex.detail}</li>
                ))}
                {!unlocked && (
                  <li className="text-gray-400 italic">[Locked content hidden...]</li>
                )}
              </ul>
              {!unlocked && (
                <Button onClick={handleUnlock} className="mt-6 w-full text-white bg-[#1f2937] hover:bg-[#111827]">
                  <Unlock className="w-4 h-4 mr-2" /> Unlock Full Report – $500
                </Button>
              )}
              {unlocked && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-4">
                  <p className="font-semibold text-center">Full report unlocked. Download coming soon.</p>
                </motion.div>
              )}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
