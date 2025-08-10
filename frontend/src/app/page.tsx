'use client'
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import Layout from "@/components/layout";

interface FormField {
  id: string;
  label: string;
  placeholder: string;
  type: string;
  required: boolean;
}

interface Template {
  name: string;
  display_name: string;
}

export default function PreviewPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [formFields, setFormFields] = useState<FormField[]>([]);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [publicPreviewUrl, setPublicPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const BASE_URL = process.env.NEXT_PUBLIC_API_URL;

  useEffect(() => {
    // Load templates and form fields on component mount
    const loadData = async () => {
      try {
        // Load templates
        const templatesRes = await fetch(`${BASE_URL}/templates`);
        const templatesData = await templatesRes.json();
        setTemplates(templatesData.templates || []);

        // Load form fields
        const fieldsRes = await fetch(`${BASE_URL}/form-fields`);
        const fieldsData = await fieldsRes.json();
        setFormFields(fieldsData.fields || []);

        // Initialize form data with empty values
        const initialFormData: Record<string, string> = {};
        fieldsData.fields?.forEach((field: FormField) => {
          initialFormData[field.id] = "";
        });
        setFormData(initialFormData);
      } catch (error) {
        console.error("Failed to load data:", error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [BASE_URL]);

  const handleFormChange = (fieldId: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [fieldId]: value
    }));
  };

  const handleSubmit = async () => {
    if (!selectedTemplate) {
      alert("Please select a template");
      return;
    }

    // Check required fields
    const requiredFields = formFields.filter(field => field.required);
    const missingFields = requiredFields.filter(field => !formData[field.id]?.trim());
    
    if (missingFields.length > 0) {
      alert(`Please fill in all required fields: ${missingFields.map(f => f.label).join(', ')}`);
      return;
    }

    setSubmitting(true);

    try {
      const response = await fetch(`${BASE_URL}/document/fill`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_name: selectedTemplate,
          form_data: {
            company_legal_name: formData.company_legal_name,
            company_state: formData.company_state,
            governing_law_state: formData.governing_law_state,
            investor_name: formData.investor_name,
            investor_title: formData.investor_title,
            investor_address: formData.investor_address,
            investor_email: formData.investor_email,
            purchase_amount: parseFloat(formData.purchase_amount),
            execution_date: formData.execution_date,
            valuation_cap: parseFloat(formData.valuation_cap),
            company_signatory_name: formData.company_signatory_name,
            company_signatory_title: formData.company_signatory_title,
            company_signatory_address: formData.company_signatory_address,
            company_signatory_email: formData.company_signatory_email
          }
        }),
      });

      const data = await response.json();
      
      if (data.success) {
        setPublicPreviewUrl(data.public_preview_url);
      } else {
        alert("Failed to generate document");
      }
    } catch (error) {
      alert("Failed to generate document");
      console.error("Error:", error);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="py-16 px-4">
          <div className="max-w-2xl mx-auto text-center">
            <div className="bg-white shadow-xl rounded-3xl p-10 border border-gray-100">
              <h1 className="text-3xl font-bold text-black mb-6">Loading...</h1>
              <p className="text-gray-600">Loading templates and form fields...</p>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white shadow-xl rounded-3xl p-10 border border-gray-100">
            <h1 className="text-3xl font-bold text-black text-center mb-6">Legal Document Generator</h1>
            <p className="text-gray-600 text-center mb-8">Select a template and fill out the form to generate your legal document</p>

            {/* Template Selection */}
            <div className="mb-8">
              <label className="block text-lg font-semibold text-black mb-3">Select Document Template</label>
              <select 
                value={selectedTemplate} 
                onChange={(e) => setSelectedTemplate(e.target.value)}
                className="w-full border rounded-md p-3 text-black bg-white"
              >
                <option value="">Choose a template...</option>
                {templates.map((template) => (
                  <option key={template.name} value={template.name}>
                    {template.display_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Form Fields */}
            {selectedTemplate && (
              <div className="space-y-6">
                <h2 className="text-2xl font-semibold text-black mb-4">Document Details</h2>
                
                {/* Company Details Section */}
                <div className="border-l-4 border-blue-500 pl-4">
                  <h3 className="text-lg font-semibold text-black mb-3">Company Details</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {formFields.slice(0, 3).map((field) => (
                      <div key={field.id} className="space-y-1">
                        <label className="block font-medium text-black">
                          {field.label} {field.required && <span className="text-red-500">*</span>}
                        </label>
                        <input 
                          type={field.type} 
                          className="w-full border rounded-md p-2 text-black" 
                          value={formData[field.id] || ""} 
                          onChange={(e) => handleFormChange(field.id, e.target.value)}
                          required={field.required}
                        />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Investor Details Section */}
                <div className="border-l-4 border-green-500 pl-4">
                  <h3 className="text-lg font-semibold text-black mb-3">Investor Details</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {formFields.slice(3, 7).map((field) => (
                      <div key={field.id} className="space-y-1">
                        <label className="block font-medium text-black">
                          {field.label} {field.required && <span className="text-red-500">*</span>}
                        </label>
                        {field.type === 'textarea' ? (
                          <textarea 
                            className="w-full border rounded-md p-2 text-black" 
                            rows={3}
                            value={formData[field.id] || ""} 
                            onChange={(e) => handleFormChange(field.id, e.target.value)}
                            required={field.required}
                          />
                        ) : (
                          <input 
                            type={field.type} 
                            className="w-full border rounded-md p-2 text-black" 
                            value={formData[field.id] || ""} 
                            onChange={(e) => handleFormChange(field.id, e.target.value)}
                            required={field.required}
                          />
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Purchase & Agreement Details Section */}
                <div className="border-l-4 border-purple-500 pl-4">
                  <h3 className="text-lg font-semibold text-black mb-3">Purchase & Agreement Details</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {formFields.slice(7, 10).map((field) => (
                      <div key={field.id} className="space-y-1">
                        <label className="block font-medium text-black">
                          {field.label} {field.required && <span className="text-red-500">*</span>}
                        </label>
                        <input 
                          type={field.type} 
                          className="w-full border rounded-md p-2 text-black" 
                          value={formData[field.id] || ""} 
                          onChange={(e) => handleFormChange(field.id, e.target.value)}
                          required={field.required}
                        />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Company Signatory Details Section */}
                <div className="border-l-4 border-orange-500 pl-4">
                  <h3 className="text-lg font-semibold text-black mb-3">Company Signatory Details</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {formFields.slice(10).map((field) => (
                      <div key={field.id} className="space-y-1">
                        <label className="block font-medium text-black">
                          {field.label} {field.required && <span className="text-red-500">*</span>}
                        </label>
                        {field.type === 'textarea' ? (
                          <textarea 
                            className="w-full border rounded-md p-2 text-black" 
                            rows={3}
                            value={formData[field.id] || ""} 
                            onChange={(e) => handleFormChange(field.id, e.target.value)}
                            required={field.required}
                          />
                        ) : (
                          <input 
                            type={field.type} 
                            className="w-full border rounded-md p-2 text-black" 
                            value={formData[field.id] || ""} 
                            onChange={(e) => handleFormChange(field.id, e.target.value)}
                            required={field.required}
                          />
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <Button 
                  onClick={handleSubmit} 
                  disabled={submitting || !selectedTemplate} 
                  className="w-full bg-black font-bold hover:bg-gray-800 text-white transition-colors duration-200 mt-8"
                >
                  {submitting ? "Generating Document..." : "Generate Document"}
                </Button>
              </div>
            )}
          </div>

          {publicPreviewUrl && (
            <div className="mt-8 bg-white shadow-xl rounded-3xl p-8 border border-gray-100">
              <h2 className="text-2xl font-semibold text-black mb-4 text-center">Your Document is Ready!</h2>
              <div className="text-center mb-4">
                <a 
                  href={publicPreviewUrl} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition-colors duration-200"
                >
                  Download Document
                </a>
              </div>
              <iframe 
                src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(publicPreviewUrl)}`} 
                style={{ width: '100%', height: '600px' }} 
                frameBorder="0"
                className="border rounded-lg"
              />
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
