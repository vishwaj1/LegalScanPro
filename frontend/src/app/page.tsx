'use client'
import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import Layout from "@/components/layout";

export default function PreviewPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [questions, setQuestions] = useState<{ placeholder: string; question: string }[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [publicPreviewUrl, setPublicPreviewUrl] = useState<string | null>(null);
  const [mode, setMode] = useState<"form" | "chatbot" | null>(null);
  const [chatIndex, setChatIndex] = useState(0);
  const [chatHistory, setChatHistory] = useState<{ role: "user" | "bot"; text: string }[]>([]);
  const [chatInput, setChatInput] = useState("");
  const chatBoxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [chatHistory]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setQuestions([]);
      setSessionId(null);
      setAnswers([]);
      setMode(null);
      setPublicPreviewUrl(null);
      setChatIndex(0);
      setChatHistory([]);
      setChatInput("");
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", selectedFile);
    try {
      const res = await fetch("http://localhost:8000/template-fill/start", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      const fields = data.questions.fields || data.questions;
      setQuestions(fields);
      setSessionId(data.session_id);
      setAnswers(new Array(fields.length).fill(""));
    } catch (error) {
      console.error("Upload failed", error);
    } finally {
      setUploading(false);
    }
  };

  const handleAnswerChange = (index: number, value: string) => {
    setAnswers(prev => {
      const newAnswers = [...prev];
      newAnswers[index] = value.trim();
      return newAnswers;
    });
  };

  const handleSubmitAnswers = async () => {
    if (!sessionId) return;
    
    // console.log("Answers array:", answers);
    // console.log("Questions length:", questions.length);
    // console.log("Answers length:", answers.length);
    
    // const unanswered = questions.filter((_, i) => !answers[i] || answers[i].trim() === "");
    // console.log("Unanswered questions:", unanswered);
    
    // if (unanswered.length > 0) {
    //   alert("Please fill all fields");
    //   return;
    // }

    setSubmitting(true);
    
    // Convert answers array to ordered array format that backend expects
    const orderedAnswers = questions.map((q, index) => ({
      placeholder: q.placeholder,
      answer: answers[index],
      index: index
    }));

    try {
      const res = await fetch("http://localhost:8000/template-fill/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, answers: orderedAnswers }),
      });
      const data = await res.json();
      setPublicPreviewUrl(data.public_preview_url);
    } catch (error) {
      alert("Failed to generate document");
      console.error("Error:", error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleChatSubmit = () => {
    if (!chatInput.trim() || !questions[chatIndex]) return;
    const newAnswers = [...answers];
    newAnswers[chatIndex] = chatInput.trim();
    setAnswers(newAnswers);
    const newHistory = [...chatHistory, { role: "user" as const, text: chatInput.trim() }];
    setChatInput("");
    if (chatIndex + 1 < questions.length) {
      newHistory.push({ role: "bot" as const, text: questions[chatIndex + 1].question });
      setChatIndex(chatIndex + 1);
    } else {
      setMode(null);
      setTimeout(() => {
        handleSubmitAnswers();
      }, 0);
    }
    setChatHistory(newHistory);
  };

  return (
    <Layout>
      <div className="py-16 px-4">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white shadow-xl rounded-3xl p-10 border border-gray-100">
            <h1 className="text-3xl font-bold text-black text-center mb-6">Upload Legal Documents</h1>
            <div className="flex flex-col items-center gap-4">
              <input type="file" onChange={handleFileChange} accept=".pdf,.doc,.docx,.zip" className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-[#f3f4f6] hover:file:bg-[#e5e7eb]" />
              <p className="text-sm text-gray-500 mt-1">Supported formats: PDF, DOC, DOCX, ZIP</p>
              <Button onClick={handleUpload} disabled={uploading || !selectedFile} className="w-full bg-black font-bold hover:bg-gray-800 text-white transition-colors duration-200">
                {uploading ? "Uploading..." : "Upload Document"}
              </Button>
            </div>
          </div>

          {questions.length > 0 && (
            <div className="mt-6 text-center space-x-4">
              <Button onClick={() => setMode("form")} className="bg-blue-600 hover:bg-blue-700 text-white">Fill via Form</Button>
              <Button onClick={() => { setMode("chatbot"); setChatHistory([{ role: "bot" as const, text: questions[0].question }]); }} className="bg-green-600 hover:bg-green-700 text-white">Fill via Chatbot</Button>
            </div>
          )}

          {mode === "form" && questions.length > 0 && (
            <div className="mt-10 bg-white shadow-xl rounded-3xl p-8 border border-gray-100">
              <h2 className="text-2xl font-semibold text-black mb-4 text-center">Please answer the following:</h2>
              <div className="space-y-4">
                {questions.map((q, idx) => (
                  <div key={idx} className="space-y-1">
                    <label className="block font-medium text-black">{q.question}</label>
                    <input type="text" className="w-full border rounded-md p-2 text-black" value={answers[idx] || ""} onChange={e => handleAnswerChange(idx, e.target.value)} />
                  </div>
                ))}
                <Button onClick={handleSubmitAnswers} disabled={submitting} className="w-full bg-[#1f2937] hover:bg-[#111827] text-white">
                  {submitting ? "Generating Document..." : "Generate Completed Document"}
                </Button>
              </div>
            </div>
          )}

          {mode === "chatbot" && (
            <div className="mt-10 bg-white shadow-xl rounded-3xl p-8 border border-gray-100">
              <div ref={chatBoxRef} className="space-y-2 max-h-96 overflow-y-auto p-2 border border-gray-200 rounded-md bg-gray-50">
                {chatHistory.map((line, i) => (
                  <div key={i} className={`whitespace-pre-wrap px-4 py-2 rounded-lg ${line.role === 'bot' ? 'bg-white text-black self-start' : 'bg-blue-600 text-white self-end'}`}>{line.text}</div>
                ))}
              </div>
              <div className="mt-4 flex gap-2">
                <input type="text" className="w-full border p-2 rounded-md text-black" value={chatInput} onChange={e => setChatInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleChatSubmit()} />
                <Button onClick={handleChatSubmit} className="bg-black text-white">Send</Button>
              </div>
            </div>
          )}

          {publicPreviewUrl && (
            <div className="mt-6 text-center">
              <iframe src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(publicPreviewUrl)}`} style={{ width: '100%', height: '600px' }} frameBorder="0"></iframe>
              <a href={publicPreviewUrl} target="_blank" rel="noopener noreferrer" className="mt-2 block text-blue-600 underline text-lg">
                Download Completed Document
              </a>
            </div>
          )}

        </div>
      </div>
    </Layout>
  );
}
