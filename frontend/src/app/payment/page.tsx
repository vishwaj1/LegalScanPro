"use client";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Lock } from "lucide-react";
import Layout from "@/components/layout";

export default function PaymentPage() {
  const router = useRouter();

  const handleFakeStripePayment = () => {
    // Simulate payment and redirect
    setTimeout(() => {
      router.push("/report");
    }, 1500);
  };

  return (
    <Layout>
      <div className="py-20 px-4">
        <div className="max-w-md mx-auto bg-white p-10 shadow-xl rounded-3xl border border-gray-100 text-center">
          <Lock className="w-12 h-12 text-[#0f172a] mx-auto mb-4" />
          <h2 className="text-2xl text-black font-bold mb-4">Unlock Full Report</h2>
          <p className="text-gray-500 mb-6 text-sm">
            One-time payment of <span className="font-semibold text-gray-700">$500</span> to view all issues, download the full report, and optionally forward to a lawyer.
          </p>
          <Button onClick={handleFakeStripePayment} className="w-full bg-[#0f172a] hover:bg-[#1e293b] text-white text-lg py-2">
            Pay with Stripe
          </Button>
          <p className="mt-3 text-xs text-gray-400">Secure checkout powered by Stripe</p>
        </div>
      </div>
    </Layout>
  );
}
