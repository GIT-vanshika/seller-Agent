"use client";

import { useEffect, useState, useRef } from "react";

interface Product {
  id: string;
  name: string;
  description: string;
  listed_price: number;
  category: string;
}

interface Evidence {
  id: string;
  product_id: string;
  type: string;
  source: string;
  label: string;
  content: string;
}

interface ValidatedDeal {
  product_id: string;
  quantity: number;
  listed_price: number;
  proposed_unit_price: number;
  effective_unit_price: number;
  total_payable_amount: number;
  pricing_mode: "fixed" | "negotiable";
  is_valid: boolean;
  validation_code: string;
  validation_message: string;
  applied_rule_description: string;
  validation_hash: string;
}

interface ChatMessage {
  sender: "buyer" | "agent";
  text: string;
  intent?: string;
  validated_deal?: ValidatedDeal;
}

interface RazorpayOrderResponse {
  order_id: string;
  status: string;
  amount_in_paisa: number;
  currency: string;
  receipt: string;
  product_id: string;
  quantity: number;
  effective_unit_price: number;
  total_payable_amount: number;
  validation_hash: string;
  message: string;
}

const API_BASE = "http://127.0.0.1:8000";

export default function Home() {
  const [backendStatus, setBackendStatus] = useState<"Loading..." | "Connected" | "Disconnected">("Loading...");
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string>("prod_003");
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  
  const [sessionId, setSessionId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState<string>("");
  const [isSending, setIsSending] = useState<boolean>(false);
  
  const [activeDeal, setActiveDeal] = useState<ValidatedDeal | null>(null);
  const [orderResult, setOrderResult] = useState<RazorpayOrderResponse | null>(null);
  const [orderError, setOrderError] = useState<string | null>(null);
  const [isCreatingOrder, setIsCreatingOrder] = useState<boolean>(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // 1. Health check & fetch products on mount
  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((res) => res.json())
      .then((data) => setBackendStatus(data.status === "ok" ? "Connected" : "Disconnected"))
      .catch(() => setBackendStatus("Disconnected"));

    fetch(`${API_BASE}/products`)
      .then((res) => res.json())
      .then((data) => {
        if (data.products && data.products.length > 0) {
          setProducts(data.products);
        }
      })
      .catch((err) => console.error("Failed to fetch products:", err));
  }, []);

  // 2. Fetch product detail & evidence whenever selected product changes
  useEffect(() => {
    if (!selectedProductId) return;
    fetch(`${API_BASE}/products/${selectedProductId}`)
      .then((res) => res.json())
      .then((data) => {
        setSelectedProduct(data.product);
        setEvidenceList(data.evidence || []);
        // Reset chat session state for new product selection
        const newSessId = `sess_${Math.random().toString(36).substring(2, 9)}`;
        setSessionId(newSessId);
        setMessages([
          {
            sender: "agent",
            text: `Hello! I am your AI Purchase Confidence & Deal Agent for **${data.product.name}**.\nListed MRP: ₹${data.product.listed_price.toFixed(2)}.\nHow can I help boost your purchase confidence today?`,
          },
        ]);
        setActiveDeal(null);
        setOrderResult(null);
        setOrderError(null);
      })
      .catch((err) => console.error("Failed to fetch product details:", err));
  }, [selectedProductId]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 3. Send message handler
  const handleSendMessage = async (textToSend?: string) => {
    const text = textToSend || inputText;
    if (!text.trim() || isSending) return;

    const userMsg: ChatMessage = { sender: "buyer", text };
    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputText("");
    setIsSending(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          product_id: selectedProductId,
          message: text,
        }),
      });

      if (!res.ok) throw new Error(`HTTP error ${res.status}`);

      const data = await res.json();
      setSessionId(data.session_id);

      const agentMsg: ChatMessage = {
        sender: "agent",
        text: data.message,
        intent: data.intent,
        validated_deal: data.validated_deal || undefined,
      };

      setMessages((prev) => [...prev, agentMsg]);

      if (data.validated_deal) {
        setActiveDeal(data.validated_deal);
      }
    } catch (err) {
      console.error("Failed to send message:", err);
      setMessages((prev) => [
        ...prev,
        { sender: "agent", text: "Sorry, I encountered an issue processing your request. Please try again." },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  // 4. Razorpay Order Creation Handler (Guarded by Pre-Checkout Deal Validation)
  const handleCreateRazorpayOrder = async () => {
    if (!activeDeal || !activeDeal.is_valid) {
      setOrderError("Cannot create order: No valid deal terms confirmed!");
      return;
    }

    setIsCreatingOrder(true);
    setOrderError(null);

    try {
      const res = await fetch(`${API_BASE}/create-order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          product_id: activeDeal.product_id,
          quantity: activeDeal.quantity,
          effective_unit_price: activeDeal.effective_unit_price,
          total_payable_amount: activeDeal.total_payable_amount,
          validation_hash: activeDeal.validation_hash,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Order creation failed");
      }

      setOrderResult(data);
    } catch (err: any) {
      setOrderError(err.message || "Failed to create Razorpay Order.");
    } finally {
      setIsCreatingOrder(false);
    }
  };

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "1.5rem", fontFamily: "system-ui, -apple-system, sans-serif", color: "#1e293b", backgroundColor: "#f8fafc", minHeight: "100vh" }}>
      {/* Header */}
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "2px solid #e2e8f0", paddingBottom: "1rem", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
            AI Purchase Confidence &amp; Deal Agent
          </h1>
          <p style={{ fontSize: "0.875rem", color: "#64748b", marginTop: "0.25rem" }}>
            Policy-Bounded Agent • Deterministic Deal Consistency • Pre-Checkout Money Safety
          </p>
        </div>
        <div style={{ padding: "0.4rem 0.8rem", borderRadius: "9999px", fontSize: "0.85rem", fontWeight: "600", backgroundColor: backendStatus === "Connected" ? "#dcfce7" : "#fee2e2", color: backendStatus === "Connected" ? "#166534" : "#991b1b" }}>
          Backend: {backendStatus}
        </div>
      </header>

      {/* Main Grid Layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: "1.5rem" }}>
        {/* Left Column: Product Selector, Specs & Quality Evidence */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Product Picker */}
          <div style={{ backgroundColor: "#ffffff", padding: "1.25rem", borderRadius: "12px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0" }}>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: "600", color: "#475569", marginBottom: "0.5rem" }}>
              Select Showcase Product:
            </label>
            <select
              value={selectedProductId}
              onChange={(e) => setSelectedProductId(e.target.value)}
              style={{ width: "100%", padding: "0.6rem 0.8rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.95rem", backgroundColor: "#f8fafc", cursor: "pointer" }}
            >
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} — ₹{p.listed_price.toFixed(2)} ({p.category})
                </option>
              ))}
            </select>

            {selectedProduct && (
              <div style={{ marginTop: "1rem", paddingTop: "0.75rem", borderTop: "1px solid #f1f5f9" }}>
                <span style={{ fontSize: "0.75rem", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "#2563eb", backgroundColor: "#eff6ff", padding: "0.2rem 0.5rem", borderRadius: "4px" }}>
                  {selectedProduct.category}
                </span>
                <h3 style={{ fontSize: "1.2rem", fontWeight: "700", marginTop: "0.5rem", marginBottom: "0.25rem", color: "#0f172a" }}>
                  {selectedProduct.name}
                </h3>
                <p style={{ fontSize: "0.875rem", color: "#475569", lineHeight: "1.4" }}>
                  {selectedProduct.description}
                </p>
                <div style={{ marginTop: "0.75rem", fontSize: "1.25rem", fontWeight: "800", color: "#059669" }}>
                  Listed MRP: ₹{selectedProduct.listed_price.toFixed(2)}
                </div>
              </div>
            )}
          </div>

          {/* Evidence Showcase */}
          <div style={{ backgroundColor: "#ffffff", padding: "1.25rem", borderRadius: "12px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0" }}>
            <h4 style={{ fontSize: "1rem", fontWeight: "700", color: "#0f172a", marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              🛡️ Product Quality &amp; Trust Evidence
            </h4>

            {evidenceList.length === 0 ? (
              <p style={{ fontSize: "0.85rem", color: "#94a3b8", fontStyle: "italic" }}>No evidence loaded.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", maxHeight: "280px", overflowY: "auto", paddingRight: "0.25rem" }}>
                {evidenceList.map((ev) => (
                  <div key={ev.id} style={{ padding: "0.75rem", borderRadius: "8px", border: "1px solid #e2e8f0", backgroundColor: ev.source === "seller_reality" ? "#f0fdf4" : ev.source === "customer_experience" ? "#faf5ff" : "#f8fafc" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.25rem" }}>
                      <span style={{ fontSize: "0.75rem", fontWeight: "700", color: ev.source === "seller_reality" ? "#166534" : ev.source === "customer_experience" ? "#6b21a8" : "#1e40af" }}>
                        [{ev.source.replace("_", " ").toUpperCase()}] {ev.label}
                      </span>
                      <span style={{ fontSize: "0.7rem", color: "#64748b", textTransform: "capitalize" }}>
                        {ev.type}
                      </span>
                    </div>
                    <p style={{ fontSize: "0.85rem", color: "#334155", margin: 0, lineHeight: "1.3" }}>
                      {ev.content}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Interactive Buyer Chat & Validated Deal Checkout */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {/* Chat Container */}
          <div style={{ backgroundColor: "#ffffff", borderRadius: "12px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0", display: "flex", flexDirection: "column", height: "520px" }}>
            {/* Chat Header */}
            <div style={{ padding: "0.85rem 1.25rem", borderBottom: "1px solid #f1f5f9", backgroundColor: "#0f172a", color: "#ffffff", borderRadius: "12px 12px 0 0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: "600", fontSize: "0.95rem" }}>💬 Buyer Chat &amp; Negotiation Assistant</span>
              <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Session: {sessionId}</span>
            </div>

            {/* Message History */}
            <div style={{ flex: 1, padding: "1rem", overflowY: "auto", display: "flex", flexDirection: "column", gap: "0.75rem", backgroundColor: "#f8fafc" }}>
              {messages.map((msg, idx) => (
                <div key={idx} style={{ alignSelf: msg.sender === "buyer" ? "flex-end" : "flex-start", maxWidth: "82%" }}>
                  <div
                    style={{
                      padding: "0.75rem 1rem",
                      borderRadius: msg.sender === "buyer" ? "16px 16px 2px 16px" : "16px 16px 16px 2px",
                      backgroundColor: msg.sender === "buyer" ? "#2563eb" : "#ffffff",
                      color: msg.sender === "buyer" ? "#ffffff" : "#0f172a",
                      boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
                      border: msg.sender === "agent" ? "1px solid #e2e8f0" : "none",
                      fontSize: "0.9rem",
                      whiteSpace: "pre-line",
                      lineHeight: "1.4",
                    }}
                  >
                    {msg.text}
                  </div>
                  {msg.intent && (
                    <span style={{ fontSize: "0.7rem", color: "#64748b", marginTop: "0.2rem", display: "block", textAlign: msg.sender === "buyer" ? "right" : "left" }}>
                      Intent: {msg.intent.replace("_", " ")}
                    </span>
                  )}
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* Quick Action Suggestion Chips */}
            <div style={{ padding: "0.5rem 1rem", backgroundColor: "#ffffff", borderTop: "1px solid #f1f5f9", display: "flex", gap: "0.5rem", overflowX: "auto" }}>
              <button
                onClick={() => handleSendMessage("Is the product quality authentic?")}
                style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem", borderRadius: "9999px", border: "1px solid #cbd5e1", backgroundColor: "#f1f5f9", cursor: "pointer", whiteSpace: "nowrap" }}
              >
                🔍 Quality Evidence?
              </button>
              <button
                onClick={() => handleSendMessage(`Can I get this for ₹${((selectedProduct?.listed_price || 1000) * 0.85).toFixed(0)}?`)}
                style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem", borderRadius: "9999px", border: "1px solid #cbd5e1", backgroundColor: "#f1f5f9", cursor: "pointer", whiteSpace: "nowrap" }}
              >
                🏷️ Offer 15% Off
              </button>
              <button
                onClick={() => handleSendMessage("What is the bulk price for 5 units?")}
                style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem", borderRadius: "9999px", border: "1px solid #cbd5e1", backgroundColor: "#f1f5f9", cursor: "pointer", whiteSpace: "nowrap" }}
              >
                📦 Bulk 5 Units
              </button>
              <button
                onClick={() => handleSendMessage("I want to proceed to checkout now")}
                style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem", borderRadius: "9999px", border: "1px solid #cbd5e1", backgroundColor: "#f1f5f9", cursor: "pointer", whiteSpace: "nowrap" }}
              >
                🛒 Proceed Checkout
              </button>
            </div>

            {/* Input Bar */}
            <div style={{ padding: "0.75rem 1rem", borderTop: "1px solid #e2e8f0", backgroundColor: "#ffffff", borderRadius: "0 0 12px 12px", display: "flex", gap: "0.5rem" }}>
              <input
                type="text"
                placeholder="Type your message or offer (e.g. 'Can I get for ₹1800 for 5 units?')..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
                disabled={isSending}
                style={{ flex: 1, padding: "0.6rem 0.8rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.9rem" }}
              />
              <button
                onClick={() => handleSendMessage()}
                disabled={isSending || !inputText.trim()}
                style={{ padding: "0.6rem 1.25rem", backgroundColor: "#2563eb", color: "#ffffff", fontWeight: "600", borderRadius: "8px", border: "none", cursor: "pointer", opacity: isSending || !inputText.trim() ? 0.6 : 1 }}
              >
                {isSending ? "..." : "Send"}
              </button>
            </div>
          </div>

          {/* Validated Deal Summary & Money Safety Pre-Checkout Card */}
          {activeDeal && (
            <div style={{ backgroundColor: activeDeal.is_valid ? "#f0fdf4" : "#fef2f2", padding: "1.25rem", borderRadius: "12px", border: `1px solid ${activeDeal.is_valid ? "#bbf7d0" : "#fecaca"}`, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <h4 style={{ margin: 0, fontSize: "1rem", fontWeight: "700", color: activeDeal.is_valid ? "#166534" : "#991b1b" }}>
                  {activeDeal.is_valid ? "✅ Deterministically Validated Deal" : "⚠️ Deal Term Validation Error"}
                </h4>
                <span style={{ fontSize: "0.75rem", fontWeight: "700", textTransform: "uppercase", padding: "0.2rem 0.5rem", borderRadius: "4px", backgroundColor: activeDeal.pricing_mode === "fixed" ? "#e0f2fe" : "#fef3c7", color: activeDeal.pricing_mode === "fixed" ? "#0369a1" : "#92400e" }}>
                  Mode: {activeDeal.pricing_mode}
                </span>
              </div>

              <p style={{ fontSize: "0.85rem", color: activeDeal.is_valid ? "#15803d" : "#b91c1c", marginBottom: "0.75rem", lineHeight: "1.3" }}>
                {activeDeal.applied_rule_description} ({activeDeal.validation_message})
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1.2fr", gap: "0.75rem", backgroundColor: "#ffffff", padding: "0.75rem", borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: "0.85rem", marginBottom: "1rem" }}>
                <div>
                  <span style={{ color: "#64748b", display: "block", fontSize: "0.75rem" }}>Effective Unit Price</span>
                  <strong style={{ fontSize: "1.1rem", color: "#0f172a" }}>₹{activeDeal.effective_unit_price.toFixed(2)}</strong>
                </div>
                <div>
                  <span style={{ color: "#64748b", display: "block", fontSize: "0.75rem" }}>Quantity</span>
                  <strong style={{ fontSize: "1.1rem", color: "#0f172a" }}>{activeDeal.quantity} unit(s)</strong>
                </div>
                <div>
                  <span style={{ color: "#64748b", display: "block", fontSize: "0.75rem" }}>Total Payable</span>
                  <strong style={{ fontSize: "1.15rem", color: "#059669" }}>₹{activeDeal.total_payable_amount.toFixed(2)}</strong>
                </div>
              </div>

              <div style={{ fontSize: "0.7rem", color: "#64748b", fontFamily: "monospace", marginBottom: "0.75rem", wordBreak: "break-all" }}>
                HMAC Security Hash: {activeDeal.validation_hash}
              </div>

              {/* Checkout Button */}
              {activeDeal.is_valid && !orderResult && (
                <button
                  onClick={handleCreateRazorpayOrder}
                  disabled={isCreatingOrder}
                  style={{ width: "100%", padding: "0.75rem", backgroundColor: "#059669", color: "#ffffff", fontWeight: "700", borderRadius: "8px", border: "none", fontSize: "1rem", cursor: "pointer", boxShadow: "0 2px 4px rgba(0,0,0,0.1)" }}
                >
                  {isCreatingOrder ? "Securing Razorpay Order..." : `💳 Lock Deal & Pay ₹${activeDeal.total_payable_amount.toFixed(2)} via Razorpay`}
                </button>
              )}

              {/* Order Creation Confirmation Modal / Result Card */}
              {orderResult && (
                <div style={{ marginTop: "0.75rem", padding: "1rem", backgroundColor: "#ecfdf5", border: "1px solid #10b981", borderRadius: "8px" }}>
                  <div style={{ fontSize: "0.95rem", fontWeight: "700", color: "#065f46", marginBottom: "0.4rem" }}>
                    🎉 Razorpay Order Created Successfully!
                  </div>
                  <div style={{ fontSize: "0.85rem", color: "#047857", lineHeight: "1.4" }}>
                    <div><strong>Order ID:</strong> {orderResult.order_id}</div>
                    <div><strong>Receipt:</strong> {orderResult.receipt}</div>
                    <div><strong>Amount:</strong> ₹{orderResult.total_payable_amount.toFixed(2)} ({orderResult.amount_in_paisa} paisa)</div>
                    <div><strong>Status:</strong> {orderResult.status.toUpperCase()}</div>
                  </div>
                  <p style={{ fontSize: "0.75rem", color: "#065f46", marginTop: "0.5rem", marginBottom: 0, fontStyle: "italic" }}>
                    {orderResult.message}
                  </p>
                </div>
              )}

              {orderError && (
                <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "#dc2626", fontWeight: "600" }}>
                  ⚠️ {orderError}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
