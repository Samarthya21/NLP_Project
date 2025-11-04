"use client";
import { useState } from "react";
import axios from "axios";

export default function Page() {
  const [input, setInput] = useState("");
  const [parsed, setParsed] = useState<any>(null);
  const [mlResponse, setMLResponse] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: any) => {
    e.preventDefault();
    setLoading(true);
    setParsed(null);
    setMLResponse(null);
    try {
      const res = await axios.post("/api/book", { text: input });
      setParsed(res.data.parsed);
      setMLResponse(res.data.mlResponse);
    } catch (err: any) {
      alert("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-6 bg-gray-50">
      <h1 className="text-2xl font-semibold mb-4">Room Booking Assistant</h1>
      <form onSubmit={handleSubmit} className="flex flex-col items-center gap-4 w-full max-w-md">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. Reserve SJT 315 11 Sept 14:00 to 16:00"
          className="w-full border p-3 rounded-lg shadow-sm"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Processing..." : "Submit"}
        </button>
      </form>

      {parsed && (
        <div className="mt-8 w-full max-w-2xl">
          <h2 className="text-lg font-medium mb-2">Parsed Request</h2>
          <pre className="bg-white p-4 rounded-lg shadow overflow-x-auto text-sm">
            {JSON.stringify(parsed, null, 2)}
          </pre>
        </div>
      )}

      {mlResponse && (
        <div className="mt-8 w-full max-w-2xl">
          <h2 className="text-lg font-medium mb-2">ML Server Response</h2>
          <pre className="bg-white p-4 rounded-lg shadow overflow-x-auto text-sm">
            {JSON.stringify(mlResponse, null, 2)}
          </pre>
        </div>
      )}
    </main>
  );
}
