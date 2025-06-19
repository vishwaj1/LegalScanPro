'use client'
import { useState } from "react";
import { Button } from "@/components/ui/button";
// import { Unlock } from "lucide-react";
// import { motion } from "framer-motion";
// import { useRouter } from "next/navigation";
import Layout from "@/components/layout";

export default function PreviewPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [questions, setQuestions] = useState<{ placeholder: string; question: string }[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  //const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [publicPreviewUrl, setPublicPreviewUrl] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      // Reset all state when new file is selected
      setQuestions([]);
      setSessionId(null);
      setAnswers({});
      //setDownloadUrl(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", selectedFile);
    try {
      const res = await fetch(`${process.env.BACKEND}/template-fill/start`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      console.log("API Response:", data);
      if (data.questions.fields) {
        setQuestions(data.questions.fields);
      } else {
        setQuestions(data.questions);
      }
      setSessionId(data.session_id);
      
      // Initialize answers object with empty strings for all questions
      const initialAnswers: Record<string, string> = {};
      questions.forEach((q: { placeholder: string; question: string }) => {
        initialAnswers[q.placeholder] = "";
      });
      setAnswers(initialAnswers);
      
    } catch (error) {
      console.error("Upload failed", error);
    } finally {
      setUploading(false);
    }
  };

  const handleAnswerChange = (placeholder: string, value: string) => {
    setAnswers(prev => ({
      ...prev,
      [placeholder]: value.trim() // Trim whitespace
    }));
  };

  const handleSubmitAnswers = async () => {
    if (!sessionId) return;
    
    // Validate that all questions have answers
    const unansweredQuestions = questions.filter(q => !answers[q.placeholder] || answers[q.placeholder].trim() === "");
    if (unansweredQuestions.length > 0) {
      alert(`Please fill in all required fields: ${unansweredQuestions.map(q => q.question).join(", ")}`);
      return;
    }
    
    setSubmitting(true);
    console.log("Submitting answers:", answers);
    
    try {
      const res = await fetch(`${process.env.BACKEND}/template-fill/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          session_id: sessionId, 
          answers: answers 
        }),
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      const data = await res.json();
      //setDownloadUrl(data.local_download_url);
      setPublicPreviewUrl(data.public_preview_url);
      
      // Automatically trigger download
      // const a = document.createElement('a');
      // a.href = url;
      // a.download = `filled_${selectedFile?.name || 'document.docx'}`;
      // document.body.appendChild(a);
      // a.click();
      // document.body.removeChild(a);
      
    } catch (error) {
      console.error("Completion failed", error);
      alert("Failed to generate document. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  // Check if all questions have answers
  const isFormComplete = questions.length > 0 && 
    questions.every(q => answers[q.placeholder] && answers[q.placeholder].trim() !== "");

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

          {questions.length > 0 && (
            <div className="mt-10 bg-white shadow-xl rounded-3xl p-8 border border-gray-100">
              <h2 className="text-2xl font-semibold text-black mb-4 text-center">Please answer the following:</h2>
              <div className="space-y-4">
                {questions.map((q, idx) => (
                  <div key={idx} className="space-y-1">
                    <label className="block font-medium text-black">
                      {q.question} {!answers[q.placeholder] && <span className="text-red-500">*</span>}
                    </label>
                    <input
                      type="text"
                      className={`w-full border rounded-md p-2 ${
                        !answers[q.placeholder] ? 'border-red-300' : 'border-gray-300'
                      }`}
                      placeholder={`Enter ${q.question.toLowerCase()}`}
                      value={answers[q.placeholder] || ""}
                      onChange={e => handleAnswerChange(q.placeholder, e.target.value)}
                      required
                    />
                  </div>
                ))}
                <Button 
                  onClick={handleSubmitAnswers} 
                  disabled={submitting || !isFormComplete} 
                  className="w-full bg-[#1f2937] hover:bg-[#111827] text-white"
                >
                  {submitting ? "Generating Document..." : "Generate Completed Document"}
                </Button>
                
                {!isFormComplete && questions.length > 0 && (
                  <p className="text-sm text-red-500 mt-2 text-center">
                    Please fill in all {questions.length} required fields to continue
                  </p>
                )}
              </div>
            </div>
          )}

          {/* {downloadUrl && (
            <div className="mt-6 text-center">
              <a
                href={downloadUrl}
                download={`${selectedFile?.name || 'document'}`}
                className="text-blue-600 underline text-lg"
              >
                Download Completed Document
              </a>
            </div>
          )} */}

          {publicPreviewUrl && (
            <div className="mt-6 text-center">
              <iframe
              src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(publicPreviewUrl)}`}
              style={{ width: '100%', height: '600px' }}
                frameBorder="0"
              ></iframe>
              <a
                href={publicPreviewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 block text-blue-600 underline text-lg"
              >
                Download Completed Document
              </a>
            </div>
          )}

        </div>
      </div>
    </Layout>
  );
}
