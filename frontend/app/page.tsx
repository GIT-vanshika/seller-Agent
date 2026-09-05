"use client";

import React, { useEffect, useState, useRef } from "react";

interface Product {
  id: string;
  name: string;
  description: string;
  listed_price: number | string;
  category: string;
}

interface Evidence {
  id: string;
  product_id: string;
  type: string;
  source: string;
  label: string;
  content: string;
  image_url?: string;
  rating?: number;
}

interface ValidatedDeal {
  product_id: string;
  quantity: number;
  listed_price: number | string;
  proposed_unit_price: number | string;
  effective_unit_price: number | string;
  total_payable_amount: number | string;
  pricing_mode: "fixed" | "negotiable";
  is_valid: boolean;
  validation_code: string;
  validation_message: string;
  applied_rule_description: string;
}

interface ChatMessage {
  sender: "buyer" | "agent";
  text: string;
  time?: string;
  intent?: string;
  deal_status?: string;
  negotiation_round?: number;
  quantity?: number;
  validated_deal?: ValidatedDeal;
  evidence_items?: Evidence[];
}

interface RazorpayOrderResponse {
  order_id: string;
  status: string;
  amount_in_paisa: number;
  currency: string;
  receipt: string;
  product_id: string;
  quantity: number;
  effective_unit_price: number | string;
  total_payable_amount: number | string;
  key_id?: string;
  is_simulated?: boolean;
  message: string;
}

interface RazorpayVerificationResponse {
  success: boolean;
  payment_status: string;
  escrow_status: string;
  order_id: string;
  payment_id: string;
  session_id: string;
  amount_in_paisa: number;
  currency: string;
  effective_unit_price: number | string;
  total_payable_amount: number | string;
  quantity?: number;
  message: string;
}

const API_BASE = "http://127.0.0.1:8000";

const parsePrice = (price: number | string | undefined | null): number => {
  if (price === undefined || price === null) return 0;
  if (typeof price === "number") return price;
  const parsed = parseFloat(price);
  return isNaN(parsed) ? 0 : parsed;
};

const formatCurrency = (price: number | string | undefined | null, decimals: number = 0): string => {
  const num = parsePrice(price);
  return num.toLocaleString("en-IN", {
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals,
  });
};

// Authoritative Stitch image links
const STITCH_ASSETS = {
  vaseStudio: "https://lh3.googleusercontent.com/aida/AEtjO1Udy-TBs1WF6JyZYWJQO_Lywihc9iXAGSipszhFtvkNVYNlHPMcYurrbG0Sn-ET7p8bZpOT2moSAjQyMIqayTAVkBFB0aVVVpRP_bV4nLqtTLUzYMlyltv4KjF-LZkxeQqnm8YaC53CxRWzNgu0da2fh5wLvJ9wa6GyzORc2oExyNVmO5JjRTD5GHBa2MB7t-fxr9FtYrPykaSOjG9pWKBLRjCh0-50FgvYnjeMHU_3LkULAIt3s40g",
  vaseWorkshop: "https://lh3.googleusercontent.com/aida/AEtjO1Vpn6I6-8iFcxdSzg3V2_uL8NAV9G0WeunKH41xLknDZqeTi7QG-Vg4dbEyxwNhGyLggyvqtu2dYzYKHKKs9K1jZMeavLDJhvMYe_R8qpfTCMh184fgYKw3XGaURZq-s8zTcgYthUH4veLc5eruywJWo8F1zyP_ZxNp7x8y5mHBLMoLoU_n8hXuPWjBJMRO_4y8Y0hKEyRUAMpRwXlIFvTaODoS6a-Y7GzuTKp8t5kJhiTzg4iap6nElg",
  vaseInSitu: "https://lh3.googleusercontent.com/aida/AEtjO1WROxvq5XCNEZq1ahPnl8BECUhA6JlyDN0t_dn-k_dCORMK--rEwfEmMro2QnPEhYJrouuD8keJqjVihPkfUB0xs_dyB-rBleKz2_7_zvRL9-yYv4JqHxBuPPHd6Z59KbtXo_4MsdknRLcGbdeN_1cjinqr5DAIo_kl1N914ds0dFNIuu0WSLjtBPjbkLyI8WS_aooN8YaCfB7HEt09Q3fmi1fTPljg0YvRrYjpCwWn9-ykpInvwNwY",
};

// Resilient, handcrafted editorial vector visual for the ceramic vase to prevent empty broken image placeholders
function CeramicVaseIllustration({ plate }: { plate: "studio" | "workshop" | "insitu" }) {
  const isWorkshop = plate === "workshop";
  const isInSitu = plate === "insitu";

  return (
    <div className="w-full h-full relative flex items-center justify-center overflow-hidden bg-gradient-to-b from-[#181922] via-[#14151d] to-[#0f1015]">
      {/* Ambient lighting backdrop */}
      <div
        className={`absolute inset-0 transition-opacity duration-500 ${
          isWorkshop
            ? "bg-[radial-gradient(ellipse_at_top_right,#fbbf2415,transparent_65%)]"
            : isInSitu
            ? "bg-[radial-gradient(ellipse_at_center,#60a5fa15,transparent_70%)]"
            : "bg-[radial-gradient(ellipse_at_top,#f7f5f30d,transparent_60%)]"
        }`}
      />

      {/* Grid subtle studio floor line */}
      <div className="absolute bottom-0 w-full h-24 border-t border-[#2e3140]/60 bg-gradient-to-t from-[#0d0e12] to-transparent" />

      {/* Ceramic Amphora Silhouette SVG */}
      <svg
        viewBox="0 0 400 500"
        className="w-[82%] h-[82%] drop-shadow-2xl z-10 transition-transform duration-500 hover:scale-[1.02]"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="clayGlaze" x1="120" y1="80" x2="280" y2="400" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FAF8F5" />
            <stop offset="45%" stopColor="#ECE7DF" />
            <stop offset="75%" stopColor="#C9BDB1" />
            <stop offset="100%" stopColor="#8A6E55" />
          </linearGradient>

          <linearGradient id="terracottaBase" x1="140" y1="340" x2="260" y2="440" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#9C5D37" />
            <stop offset="50%" stopColor="#7B4222" />
            <stop offset="100%" stopColor="#4A2613" />
          </linearGradient>

          <linearGradient id="pedestal" x1="80" y1="430" x2="320" y2="480" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#2A2C38" />
            <stop offset="100%" stopColor="#181A22" />
          </linearGradient>

          <radialGradient id="studioShadow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#000000" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#000000" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Shadow on pedestal */}
        <ellipse cx="200" cy="435" rx="75" ry="14" fill="url(#studioShadow)" opacity="0.6" />

        {/* Display Pedestal Block */}
        <path
          d="M 60 440 L 340 440 L 320 475 L 80 475 Z"
          fill="url(#pedestal)"
          stroke="#353849"
          strokeWidth="1.5"
        />

        {/* Terracotta Unglazed Footing */}
        <path
          d="M 152 355 C 145 390 148 425 158 430 L 242 430 C 252 425 255 390 248 355 Z"
          fill="url(#terracottaBase)"
          stroke="#5C321B"
          strokeWidth="1.2"
        />

        {/* Chiseled throwing rings on terracotta */}
        <path d="M 155 380 Q 200 392 245 380" stroke="#4A2613" strokeWidth="1.5" opacity="0.6" strokeDasharray="3 2" />
        <path d="M 157 405 Q 200 416 243 405" stroke="#4A2613" strokeWidth="1.5" opacity="0.6" strokeDasharray="4 2" />

        {/* Sculptural Ceramic Vase Body */}
        <path
          d="M 188 110 
             C 188 100 212 100 212 110 
             L 210 160 
             C 245 190 268 250 260 330 
             C 255 365 245 375 235 375 
             L 165 375 
             C 155 375 145 365 140 330 
             C 132 250 155 190 190 160 
             Z"
          fill="url(#clayGlaze)"
          stroke="#47413B"
          strokeWidth="1.5"
        />

        {/* Organic Sculptural Loop Handle */}
        <path
          d="M 172 170 
             C 120 180 115 225 130 255 
             C 140 275 155 270 152 260 
             C 142 240 140 205 174 195 Z"
          fill="url(#clayGlaze)"
          stroke="#524C44"
          strokeWidth="1.5"
        />

        {/* Soft glaze reflection highlight */}
        <path
          d="M 175 180 C 160 220 162 280 170 320"
          stroke="#FFFFFF"
          strokeWidth="3.5"
          strokeLinecap="round"
          opacity="0.45"
        />

        {/* Rim detailing */}
        <ellipse cx="200" cy="110" rx="12" ry="4" fill="#6A5C50" stroke="#3D352E" strokeWidth="1" />
      </svg>
    </div>
  );
}

export default function AuraCommerceStorefront() {
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("01 Ceramics & Objects");
  const [selectedProductId, setSelectedProductId] = useState<string>("prod_004");
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);

  const [activeViewPlate, setActiveViewPlate] = useState<"studio" | "workshop" | "insitu">("studio");
  const [imageLoadFailed, setImageLoadFailed] = useState<boolean>(false);

  const [sessionId, setSessionId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState<string>("");
  const [isSending, setIsSending] = useState<boolean>(false);

  const [activeDeal, setActiveDeal] = useState<ValidatedDeal | null>(null);
  const [activeRound, setActiveRound] = useState<number>(0);
  const [activeDealStatus, setActiveDealStatus] = useState<string>("idle");
  const [citedEvidenceIds, setCitedEvidenceIds] = useState<string[]>([]);
  const [lastBuyerOfferText, setLastBuyerOfferText] = useState<string | null>(null);

  const [canShowPayment, setCanShowPayment] = useState<boolean>(false);
  const [isPaymentProcessing, setIsPaymentProcessing] = useState<boolean>(false);
  const [paymentStep, setPaymentStep] = useState<number>(0);
  const [orderResult, setOrderResult] = useState<RazorpayOrderResponse | null>(null);
  const [verifiedPayment, setVerifiedPayment] = useState<RazorpayVerificationResponse | null>(null);
  const [orderError, setOrderError] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const chatScrollContainerRef = useRef<HTMLDivElement>(null);

  // Initial load
  useEffect(() => {
    fetch(`${API_BASE}/products`)
      .then((res) => res.json())
      .then((data) => {
        if (data.products && data.products.length > 0) {
          setProducts(data.products);
        }
      })
      .catch((err) => console.error("Failed to load products:", err));
  }, []);

  // Product selection & session initialization
  useEffect(() => {
    if (!selectedProductId) return;

    fetch(`${API_BASE}/products/${selectedProductId}`)
      .then((res) => res.json())
      .then((data) => {
        setSelectedProduct(data.product);
        setEvidenceList(data.evidence || []);
        setActiveViewPlate("studio");
        setImageLoadFailed(false);

        const newSession = `sess_${Math.random().toString(36).substring(2, 9)}`;
        setSessionId(newSession);

        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

        setMessages([
          {
            sender: "agent",
            time: timeStr,
            text: `Welcome to AURA. I am your autonomous purchase intelligence and deal concierge for the **${data.product.name}**.\n\nListed MRP is ₹${formatCurrency(data.product.listed_price)}. I can help you assess this product using the available catalog information and real-world evidence before you decide. How can I help verify your confidence today?`,
          },
        ]);

        setActiveDeal(null);
        setActiveRound(0);
        setActiveDealStatus("idle");
        setCitedEvidenceIds([]);
        setLastBuyerOfferText(null);
        setOrderResult(null);
        setVerifiedPayment(null);
        setOrderError(null);
        setPaymentStep(0);
        setCanShowPayment(false);
      })
      .catch((err) => console.error("Failed to fetch product details:", err));
  }, [selectedProductId]);

  // Smooth scroll within the chat container ONLY (avoids jarring window-level page jumping)
  useEffect(() => {
    if (chatScrollContainerRef.current) {
      chatScrollContainerRef.current.scrollTo({
        top: chatScrollContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, isSending, activeDeal]);

  const handleSendMessage = async (customText?: string) => {
    const text = (customText || inputText).trim();
    if (!text || isSending) return;

    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    const priceMatch = text.match(/(?:under|for|at|pay|offer|rs\.?|₹)?\s*(\d{3,5})/i);
    if (priceMatch) {
      setLastBuyerOfferText(`₹${formatCurrency(priceMatch[1])}`);
    }

    const userMessage: ChatMessage = { sender: "buyer", text, time: timeStr };
    setMessages((prev) => [...prev, userMessage]);
    if (!customText) setInputText("");
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
      setActiveRound(data.negotiation_round || 0);
      setActiveDealStatus(data.deal_status || "negotiating");
      if (data.can_show_payment !== undefined) {
        setCanShowPayment(Boolean(data.can_show_payment));
      }

      const citedIds: string[] = [];
      if (data.evidence_items && Array.isArray(data.evidence_items)) {
        data.evidence_items.forEach((item: any) => {
          if (item.id) citedIds.push(item.id);
        });
      }
      if (citedIds.length > 0) {
        setCitedEvidenceIds(citedIds);
        if (text.toLowerCase().includes("picture") || text.toLowerCase().includes("real") || text.toLowerCase().includes("light")) {
          setActiveViewPlate("workshop");
        }
      }

      if (data.validated_deal) {
        setActiveDeal(data.validated_deal);
      }

      const agentMessage: ChatMessage = {
        sender: "agent",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        text: data.message,
        intent: data.intent,
        deal_status: data.deal_status,
        negotiation_round: data.negotiation_round,
        quantity: data.quantity,
        validated_deal: data.validated_deal || undefined,
        evidence_items: data.evidence_items || undefined,
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (err) {
      console.error("Failed to send message:", err);
      setMessages((prev) => [
        ...prev,
        {
          sender: "agent",
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          text: "I experienced a temporary communication interruption. Your commercial deal state remains preserved. Please try again.",
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  // Razorpay MVP checkout flow
  // Helper: Submits authentic or simulated signature to authoritative backend verification
  const submitPaymentVerification = async (
    orderId: string,
    paymentId: string,
    signature: string
  ) => {
    setPaymentStep(3); // Verifying Payment Signature...
    const verifyRes = await fetch(`${API_BASE}/verify-payment`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        razorpay_order_id: orderId,
        razorpay_payment_id: paymentId,
        razorpay_signature: signature,
      }),
    });

    const verifyData = await verifyRes.json();
    if (!verifyRes.ok) {
      throw new Error(verifyData.detail || "Payment signature verification failed.");
    }

    setPaymentStep(4);
    setVerifiedPayment(verifyData);
    setIsPaymentProcessing(false);
  };

  // Razorpay Authoritative Lifecycle Checkout Flow
  // Sequence: VALIDATED_DEAL -> ORDER_CREATED -> RAZORPAY_CHECKOUT -> SERVER-SIDE HMAC VERIFICATION -> PAYMENT_CAPTURED -> ESCROW_RESERVED
  const handleProceedToPayment = async () => {
    if (!activeDeal || !activeDeal.is_valid) {
      setOrderError("A valid commercial deal must be agreed before proceeding to payment.");
      return;
    }

    setIsPaymentProcessing(true);
    setPaymentStep(1); // Authenticating Deal Terms...
    setOrderError(null);

    setTimeout(() => setPaymentStep(2), 600);

    try {
      // Step 1: ORDER_CREATED (Server executes PolicyEngine & DealConsistencyValidator)
      setPaymentStep(2); // Securing Razorpay Order...
      const orderRes = await fetch(`${API_BASE}/create-order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          product_id: activeDeal.product_id,
          quantity: activeDeal.quantity,
          requested_unit_price: parsePrice(activeDeal.effective_unit_price),
          total_payable_amount: parsePrice(activeDeal.total_payable_amount),
        }),
      });

      const orderData: RazorpayOrderResponse = await orderRes.json();
      if (!orderRes.ok) {
        throw new Error(orderData.message || "Could not prepare checkout order.");
      }

      setOrderResult(orderData);

      // Step 2: DUAL-MODE CHECKOUT BRANCH (Official Razorpay Checkout Modal vs Simulation Fallback)
      const isRealRazorpay = Boolean(
        orderData.key_id && !orderData.is_simulated && typeof (window as any).Razorpay !== "undefined"
      );

      if (isRealRazorpay) {
        // Real Razorpay Test Mode Flow
        const options = {
          key: orderData.key_id,
          amount: orderData.amount_in_paisa,
          currency: orderData.currency || "INR",
          name: "AURA AI Deal Concierge",
          description: `${selectedProduct?.name || "Product Suite"} (${activeDeal.quantity} units)`,
          order_id: orderData.order_id,
          handler: async function (response: {
            razorpay_payment_id: string;
            razorpay_order_id: string;
            razorpay_signature: string;
          }) {
            try {
              await submitPaymentVerification(
                response.razorpay_order_id,
                response.razorpay_payment_id,
                response.razorpay_signature
              );
            } catch (verErr: any) {
              setIsPaymentProcessing(false);
              setPaymentStep(0);
              setOrderError(verErr.message || "Payment signature verification failed.");
            }
          },
          prefill: {
            name: "AURA Valued Buyer",
            email: "buyer@aura-agent.ai",
            contact: "9820098200",
          },
          theme: {
            color: "#10b981",
          },
          modal: {
            ondismiss: function () {
              setIsPaymentProcessing(false);
              setPaymentStep(0);
            },
          },
        };

        const rzp = new (window as any).Razorpay(options);
        rzp.on("payment.failed", function (failRes: any) {
          setIsPaymentProcessing(false);
          setPaymentStep(0);
          setOrderError(failRes.error?.description || "Payment failed on Razorpay Gateway.");
        });
        rzp.open();
      } else {
        // Safe Simulation Fallback Flow (used when Razorpay credentials are unset or during automated tests)
        setPaymentStep(3); // Verifying Payment Signature...
        const paymentId = `pay_rzp_${Math.random().toString(36).substring(2, 11)}`;

        const sigRes = await fetch(`${API_BASE}/demo/sign-payment`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            order_id: orderData.order_id,
            payment_id: paymentId,
          }),
        });
        const sigData = await sigRes.json();

        await submitPaymentVerification(
          orderData.order_id,
          paymentId,
          sigData.signature
        );
      }
    } catch (err: any) {
      setIsPaymentProcessing(false);
      setPaymentStep(0);
      setOrderError(err.message || "Unable to initiate payment. Your validated deal remains active.");
    }
  };

  const isDealAgreed = Boolean(canShowPayment && activeDeal?.is_valid);
  const isNegotiating = activeRound > 0 || activeDealStatus === "negotiating";

  const calculateSavings = (deal: ValidatedDeal | null): number => {
    if (!deal) return 0;
    const mrp = parsePrice(deal.listed_price);
    const qty = deal.quantity;
    const total = parsePrice(deal.total_payable_amount);
    const originalTotal = mrp * qty;
    return Math.max(0, originalTotal - total);
  };

  const getProductSpecs = (product: Product | null) => {
    if (!product) return [];
    if (product.id === "prod_001") {
      return [
        { label: "Origin", val: "Artisan Bakery Jaipur" },
        { label: "Dietary", val: "100% Egg-Free Veg" },
        { label: "Rating", val: "★ 4.2 (Most Reordered)" },
        { label: "Quality", val: "Pure Amul Butter" },
      ];
    }
    if (product.id === "prod_002") {
      return [
        { label: "Origin", val: "Master Creamery" },
        { label: "Base", val: "100% Pure Milk" },
        { label: "Rating", val: "★ 4.4 Verified" },
        { label: "Flavour", val: "Madagascar Vanilla" },
      ];
    }
    if (product.id === "prod_004") {
      return [
        { label: "Silhouette", val: "Minimalist Donut Pair" },
        { label: "Glaze", val: "Speckled Porous Ceramic" },
        { label: "Rating", val: "★ 4.3 (Awesome Look)" },
        { label: "Pairing", val: "Vases with Pampas Grass" },
      ];
    }
    if (product.id === "prod_003") {
      return [
        { label: "Fabric", val: "Sage Silk & Organza" },
        { label: "Craft", val: "Hand Zari Embroidery" },
        { label: "Rating", val: "★ 3.9 Verified" },
        { label: "Ensemble", val: "Kurti, Dupatta & Pant" },
      ];
    }
    if (product.id === "prod_005") {
      return [
        { label: "Material", val: "100% Organic Flax Linen" },
        { label: "Collar", val: "Resort Cuban Camp" },
        { label: "Rating", val: "★ 4.0 Verified" },
        { label: "Embroidery", val: "Botanical Slub Stitch" },
      ];
    }
    if (product.id === "prod_006") {
      return [
        { label: "Origin", val: "LuvIt Master Chocolatier" },
        { label: "Solids", val: "18% Cocoa Solids" },
        { label: "Rating", val: "★ 4.4 (Silky Texture)" },
        { label: "Form", val: "500g Slab Block" },
      ];
    }
    return [
      { label: "Category", val: product.category },
      { label: "Authentication", val: "Direct Artisan Verified" },
      { label: "Origin", val: "Direct Studio Dispatch" },
      { label: "Assurance", val: "Physical Proof Recorded" },
    ];
  };

  const getProductImageSource = (product: Product | null, plate: "studio" | "workshop" | "insitu"): string | null => {
    if (!product) return null;
    if (product.id === "prod_001") {
      if (plate === "workshop") return "/images/products/prod_001/prod_001_box_back.jpg";
      if (plate === "insitu") return "/images/products/prod_001/prod_001_table_insitu.jpg";
      return "/images/products/prod_001/prod_001_box_front.jpg";
    }
    if (product.id === "prod_002") {
      if (plate === "workshop") return "/images/products/prod_002/prod_002_lid_art.png";
      if (plate === "insitu") return "/images/products/prod_002/prod_002_waffle_cone_evidence.png";
      return "/images/products/prod_002/prod_002_tub_open.png";
    }
    if (product.id === "prod_003") {
      if (plate === "workshop") return "/images/products/prod_003/prod_003_studio_neutral.png";
      if (plate === "insitu") return "/images/products/prod_003/prod_003_mannequin_insitu.png";
      return "/images/products/prod_003/prod_003_studio_front.png";
    }
    if (product.id === "prod_004") {
      if (plate === "workshop") return "/images/products/prod_004/prod_004_texture_macro.png";
      if (plate === "insitu") return "/images/products/prod_004/prod_004_coffee_table.jpg";
      return "/images/products/prod_004/prod_004_floor_pair.jpg";
    }
    if (product.id === "prod_005") {
      if (plate === "workshop") return "/images/products/prod_005/prod_005_studio_upper.jpg";
      if (plate === "insitu") return "/images/products/prod_005/prod_005_outdoor_sunlight.jpg";
      return "/images/products/prod_005/prod_005_studio_front.png";
    }
    if (product.id === "prod_006") {
      if (plate === "workshop") return "/images/products/prod_006/prod_006_ingredients.jpg";
      if (plate === "insitu") return "/images/products/prod_006/prod_006_unwrapped_slab.png";
      return "/images/products/prod_006/prod_006_box_front.jpg";
    }
    return null;
  };

  const getViewPlateLabel = (product: Product | null, plate: "studio" | "workshop" | "insitu"): string => {
    if (product?.id === "prod_001") {
      if (plate === "workshop") return "Plate [02] · Box Nutrition & Ingredients Back";
      if (plate === "insitu") return "Plate [03] · In Situ Table Setting";
      return "Plate [01] · Official Packaged Front Box";
    }
    if (product?.id === "prod_002") {
      if (plate === "workshop") return "Plate [02] · Gourmet Tub Lid & Milk Craft";
      if (plate === "insitu") return "Plate [03] · Waffle Cone Serving Scoop";
      return "Plate [01] · Official Gourmet Whipped Tub";
    }
    if (product?.id === "prod_003") {
      if (plate === "workshop") return "Plate [02] · Studio Editorial Neutral";
      if (plate === "insitu") return "Plate [03] · Showroom Floor Reality Mannequin";
      return "Plate [01] · Official Atelier Studio Presentation";
    }
    if (product?.id === "prod_004") {
      if (plate === "workshop") return "Plate [02] · Macro Speckled Clay Porosity";
      if (plate === "insitu") return "Plate [03] · Natural Wood Coffee Table In Situ";
      return "Plate [01] · Studio Window Daylight Donut Pair";
    }
    if (product?.id === "prod_005") {
      if (plate === "workshop") return "Plate [02] · Cuban Collar & Embroidery Stitch";
      if (plate === "insitu") return "Plate [03] · Natural Daylight Patio In Situ";
      return "Plate [01] · Studio Resort Linen Archival Front";
    }
    if (product?.id === "prod_006") {
      if (plate === "workshop") return "Plate [02] · Ingredients & Cocoa Solids";
      if (plate === "insitu") return "Plate [03] · Unwrapped Scored Chocolate Slab";
      return "Plate [01] · Official Cocoa Crush Studio Box";
    }
    if (plate === "workshop") return "Plate [02] · Workshop Daylight Bench";
    if (plate === "insitu") return "Plate [03] · In Situ Kyoto Interior";
    return `Plate [01] · ${product?.name || "Studio"} Archival Neutral`;
  };

  return (
    <div suppressHydrationWarning className="bg-background text-on-surface min-h-screen flex flex-col font-body-md antialiased selection:bg-primary/30">
      {/* 1. STOREFRONT HEADER (DARK LUXURY ARCHITECTURE) */}
      <header className="sticky top-0 z-50 bg-[#0d0e12]/90 backdrop-blur-md border-b border-[#2e3140]/80">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-10 h-20 flex items-center justify-between">
          {/* Left Wordmark & Intelligence Badge */}
          <div className="flex items-center gap-4">
            <span className="font-headline-lg text-2xl tracking-widest uppercase font-semibold text-on-surface">
              AURA
            </span>
            <span className="h-4 w-[1px] bg-outline-variant/80"></span>
            <div className="flex items-center gap-2 bg-surface-container-low px-2.5 py-1 rounded border border-outline-variant/60 shadow-2xs">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary shadow-[0_0_8px_#10b981]"></span>
              <span className="font-data-mono-sm text-[11px] uppercase tracking-wider text-on-surface-variant font-medium">
                AI Purchase Confidence &amp; Deal Agent ·{" "}
                <span className="text-secondary font-semibold">Live Escrow</span>
              </span>
            </div>
          </div>

          {/* Center Editorial Categories */}
          <nav className="hidden md:flex items-center gap-8">
            <button
              onClick={() => {
                setSelectedCategory("01 Ceramics & Objects");
                setSelectedProductId("prod_004");
              }}
              className={`font-label-md text-xs uppercase tracking-widest transition-all ${
                selectedCategory.includes("Ceramics")
                  ? "text-on-surface font-semibold border-b-2 border-primary pb-1"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              01 Ceramics &amp; Objects
            </button>
            <button
              onClick={() => {
                setSelectedCategory("02 Textiles");
                setSelectedProductId("prod_003");
              }}
              className={`font-label-md text-xs uppercase tracking-widest transition-all ${
                selectedCategory.includes("Textiles")
                  ? "text-on-surface font-semibold border-b-2 border-primary pb-1"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              02 Textiles (Fashion)
            </button>
            <button
              onClick={() => {
                setSelectedCategory("03 Editions");
                setSelectedProductId("prod_001");
              }}
              className={`font-label-md text-xs uppercase tracking-widest transition-all ${
                selectedCategory.includes("Editions")
                  ? "text-on-surface font-semibold border-b-2 border-primary pb-1"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              03 Editions
            </button>
          </nav>

          {/* Right Actions */}
          <div className="flex items-center gap-4 lg:gap-6">
            <div className="hidden sm:flex items-center gap-1.5 font-label-md text-xs uppercase tracking-widest text-on-surface-variant hover:text-on-surface transition-colors cursor-pointer">
              <span className="material-symbols-outlined text-[18px] text-secondary">verified</span>
              <span>Collector Dossier</span>
            </div>

            <div className="flex items-center gap-2 pl-4 border-l border-outline-variant/60">
              <div className="relative flex items-center gap-2 bg-surface-container-high px-3.5 py-1.5 rounded border border-outline-variant/40">
                <span className="material-symbols-outlined text-[18px]">shopping_bag</span>
                <span className="font-data-mono-sm text-xs font-semibold uppercase">
                  Bag ({activeDeal ? activeDeal.quantity : 1})
                </span>
                <span className="w-1.5 h-1.5 rounded-full bg-secondary shadow-[0_0_6px_#10b981]"></span>
              </div>
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary shadow-sm">
                <span className="material-symbols-outlined text-[17px]">person</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Product Strip Selector for Instant Switching across 5 Products */}
      <section className="bg-surface-container-low/80 border-b border-outline-variant/30 py-2.5 backdrop-blur-sm">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-10 flex items-center gap-3 overflow-x-auto">
          <span className="font-data-mono-sm text-[11px] uppercase tracking-wider text-on-surface-variant shrink-0">
            Curated Collection:
          </span>
          {products.slice(0, 6).map((p) => {
            const isSelected = p.id === selectedProductId;
            return (
              <button
                key={p.id}
                onClick={() => setSelectedProductId(p.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs transition-all shrink-0 cursor-pointer ${
                  isSelected
                    ? "bg-surface-container text-on-surface border border-primary/60 font-semibold shadow-xs"
                    : "bg-surface-container-lowest text-on-surface-variant border border-outline-variant/40 hover:bg-surface-container hover:text-on-surface"
                }`}
              >
                <span>{p.name}</span>
                <span className="font-data-mono-sm tabular-nums text-[11px] text-primary">
                  ₹{formatCurrency(p.listed_price)}
                </span>
              </button>
            );
          })}
        </div>
      </section>

      {/* MAIN DUAL-STAGE EDITORIAL SURFACE (BALANCED LAPTOP SPLIT · VIEWPORT-ALIGNED) */}
      <main className="w-full max-w-[1440px] mx-auto px-4 lg:px-8 py-4 flex-1 flex flex-col min-h-0">
        <div className="flex flex-col lg:flex-row gap-6 lg:gap-8 items-stretch lg:h-[calc(100vh-8.5rem)] min-h-0">
          {/* LEFT STAGE (BALANCED PRODUCT SHOWCASE & ANCHOR · 50% WIDTH ON DESKTOP) */}
          <aside className="w-full lg:w-1/2 flex flex-col gap-3.5 h-full overflow-y-auto pr-1 pb-4">
            {/* Breadcrumb & Curation Batch */}
            <div className="flex items-center justify-between border-b border-outline-variant/50 pb-2 shrink-0">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-secondary shadow-[0_0_8px_#10b981]"></span>
                <span className="font-data-mono-sm text-xs uppercase tracking-wider text-secondary font-medium">
                  Verified Artisan Batch · No. {selectedProduct?.id.replace("prod_", "") || "04"}/12
                </span>
              </div>
              <span className="font-data-mono-sm text-[11px] uppercase tracking-widest text-secondary bg-secondary-container/40 px-2 py-0.5 rounded border border-secondary/30">
                Escrow Backed
              </span>
            </div>

            {/* Product Identity Header */}
            <div className="flex flex-col gap-1 shrink-0">
              <div className="flex items-center justify-between">
                <span className="font-label-md text-xs uppercase tracking-widest text-on-surface-variant font-medium">
                  {selectedProduct?.id === "prod_001"
                    ? "Shree Radhey Artisanal Bakers · Jaipur"
                    : selectedProduct?.id === "prod_002"
                    ? "Vadilal Master Creamery · Cold-Chain Batch"
                    : selectedProduct?.id === "prod_003"
                    ? "Atelier Veda Silk Masters · Delhi & Jaipur"
                    : selectedProduct?.id === "prod_004"
                    ? "Studio Aethel Ceramic Atelier · Khurja & Jaipur"
                    : selectedProduct?.id === "prod_005"
                    ? "Atelier Verve Resort Linens · Goa & Pondicherry"
                    : selectedProduct?.id === "prod_006"
                    ? "LuvIt Master Chocolatiers · Special Reserve"
                    : "Studio Aethel · Collection 24"}
                </span>
                {selectedProduct?.id === "prod_001" && (
                  <span className="font-data-mono-sm text-[11px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded flex items-center gap-1 shadow-xs">
                    <span>★ 4.2</span>
                    <span className="text-on-surface-variant text-[10px]">· Most Reordered</span>
                  </span>
                )}
                {selectedProduct?.id === "prod_002" && (
                  <span className="font-data-mono-sm text-[11px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded flex items-center gap-1 shadow-xs">
                    <span>★ 4.4</span>
                    <span className="text-on-surface-variant text-[10px]">· Verified Rating</span>
                  </span>
                )}
                {selectedProduct?.id === "prod_003" && (
                  <span className="font-data-mono-sm text-[11px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded flex items-center gap-1 shadow-xs">
                    <span>★ 3.9</span>
                    <span className="text-on-surface-variant text-[10px]">· Verified Rating</span>
                  </span>
                )}
                {selectedProduct?.id === "prod_004" && (
                  <span className="font-data-mono-sm text-[11px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded flex items-center gap-1 shadow-xs">
                    <span>★ 4.3</span>
                    <span className="text-on-surface-variant text-[10px]">· Verified Rating</span>
                  </span>
                )}
                {selectedProduct?.id === "prod_005" && (
                  <span className="font-data-mono-sm text-[11px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded flex items-center gap-1 shadow-xs">
                    <span>★ 4.0</span>
                    <span className="text-on-surface-variant text-[10px]">· Verified Rating</span>
                  </span>
                )}
                {selectedProduct?.id === "prod_006" && (
                  <span className="font-data-mono-sm text-[11px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded flex items-center gap-1 shadow-xs">
                    <span>★ 4.4</span>
                    <span className="text-on-surface-variant text-[10px]">· Verified Rating</span>
                  </span>
                )}
              </div>
              <h1 className="font-headline-lg text-2xl md:text-3xl text-on-surface font-normal leading-tight">
                {selectedProduct?.name || "Sculptural Ceramic Amphora Vase"}
              </h1>
              <p className="font-body-sm text-xs md:text-sm text-on-surface-variant mt-0.5 leading-relaxed">
                {selectedProduct?.description ||
                  "Wheel-thrown local stoneware, porous slip body, tactile unglazed terracotta footing with hand-etched slip markings."}
              </p>
            </div>

            {/* Primary Product Stage Image & Interactive Lens State */}
            <div className="relative w-full rounded-xl overflow-hidden bg-surface-container-low border border-outline-variant/40 shadow-md group shrink-0">
              <div className="relative w-full aspect-[4/3] md:aspect-[16/11] bg-surface-container-high overflow-hidden flex items-center justify-center">
                {/* Visual Media Stage with Real Image or Resilient Vector Fallback */}
                {getProductImageSource(selectedProduct, activeViewPlate) ? (
                  <img
                    alt={selectedProduct?.name || "Product Media"}
                    className="w-full h-full object-contain p-2 transition-opacity duration-300 bg-[#14151c]"
                    id="main-product-stage"
                    src={getProductImageSource(selectedProduct, activeViewPlate)!}
                  />
                ) : !imageLoadFailed && selectedProduct?.id === "prod_004" ? (
                  <CeramicVaseIllustration plate={activeViewPlate} />
                ) : (
                  <CeramicVaseIllustration plate={activeViewPlate} />
                )}

                {/* Studio Lens Overlay */}
                <div className="absolute top-3 left-3 flex items-center gap-2 bg-[#14151c]/90 backdrop-blur-md px-2.5 py-1 rounded border border-[#2e3140] shadow-xs">
                  <span className="material-symbols-outlined text-[14px] text-primary">lens</span>
                  <span className="font-data-mono-sm text-[11px] uppercase tracking-wide text-on-surface" id="media-state-label">
                    {getViewPlateLabel(selectedProduct, activeViewPlate)}
                  </span>
                </div>

                {/* Reactive Price Badge */}
                <div className="absolute bottom-3 right-3 bg-[#14151c]/95 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#2e3140] shadow-sm flex flex-col items-end">
                  <div className="flex items-baseline gap-2">
                    {activeDeal && parsePrice(activeDeal.effective_unit_price) < parsePrice(activeDeal.listed_price) ? (
                      <>
                        <span className="font-data-mono-sm text-xs text-on-surface-variant line-through tabular-nums">
                          ₹{formatCurrency(activeDeal.listed_price)}
                        </span>
                        <span className="font-data-mono text-base font-semibold text-on-surface tabular-nums">
                          ₹{formatCurrency(activeDeal.effective_unit_price)}
                        </span>
                      </>
                    ) : (
                      <span className="font-data-mono text-base font-semibold text-on-surface tabular-nums">
                        ₹{formatCurrency(selectedProduct?.listed_price || 0)}
                      </span>
                    )}
                  </div>
                  {activeDeal && (
                    <span className="font-label-md text-[10px] uppercase tracking-wider text-secondary font-bold">
                      Active Deal: {activeDeal.quantity} Unit{activeDeal.quantity > 1 ? "s" : ""} Applied
                    </span>
                  )}
                </div>
              </div>

              {/* Quick Angle Perspective Tabs */}
              <div className="grid grid-cols-3 gap-1 p-1.5 bg-surface-container border-t border-outline-variant/40">
                <button
                  onClick={() => setActiveViewPlate("studio")}
                  className={`view-btn flex flex-col items-center justify-center py-1.5 px-2 rounded transition-all border cursor-pointer ${
                    activeViewPlate === "studio" ? "active" : "inactive"
                  }`}
                >
                  <span className="font-data-mono-sm text-[11px] uppercase font-semibold">Studio Plate</span>
                  <span className="font-label-md text-[9px] text-on-surface-variant">Neutral 5000K</span>
                </button>
                <button
                  onClick={() => setActiveViewPlate("workshop")}
                  className={`view-btn flex flex-col items-center justify-center py-1.5 px-2 rounded transition-all border cursor-pointer ${
                    activeViewPlate === "workshop" ? "active" : "inactive"
                  }`}
                >
                  <span className="font-data-mono-sm text-[11px] uppercase font-semibold">Workshop</span>
                  <span className="font-label-md text-[9px] text-on-surface-variant">Raw Daylight</span>
                </button>
                <button
                  onClick={() => setActiveViewPlate("insitu")}
                  className={`view-btn flex flex-col items-center justify-center py-1.5 px-2 rounded transition-all border cursor-pointer ${
                    activeViewPlate === "insitu" ? "active" : "inactive"
                  }`}
                >
                  <span className="font-data-mono-sm text-[11px] uppercase font-semibold">In Situ</span>
                  <span className="font-label-md text-[9px] text-on-surface-variant">Spatial Context</span>
                </button>
              </div>
            </div>

            {/* Archival Specifications Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 shrink-0">
              {getProductSpecs(selectedProduct).map((spec, i) => (
                <div key={i} className="flex flex-col bg-surface-container-low p-2.5 rounded border border-outline-variant/40">
                  <span className="font-label-md text-[9px] uppercase tracking-widest text-on-surface-variant">
                    {spec.label}
                  </span>
                  <span className="font-data-mono-sm text-[11px] font-semibold text-on-surface mt-0.5 truncate">
                    {spec.val}
                  </span>
                </div>
              ))}
            </div>

            {/* Deal Status Indicator Bar */}
            <div className="bg-surface-container-low border border-outline-variant/40 rounded-lg p-3 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-secondary shadow-[0_0_8px_#10b981]"></div>
                <div>
                  <p className="font-label-md text-xs font-semibold text-on-surface">
                    Listed MRP ₹{formatCurrency(selectedProduct?.listed_price || 0)}
                  </p>
                  <p className="font-body-sm text-[11px] text-on-surface-variant">
                    {activeDeal
                      ? `Active Rate: ₹${formatCurrency(activeDeal.effective_unit_price)}/ea (${activeDeal.quantity} pcs)`
                      : "Volume negotiation available on 2+ units"}
                  </p>
                </div>
              </div>
              <span className="font-data-mono-sm text-[10px] text-secondary font-bold uppercase tracking-wider bg-secondary-container/40 border border-secondary/30 px-2 py-0.5 rounded">
                {isDealAgreed ? "DEAL VALIDATED" : isNegotiating ? "ACTIVE NEGOTIATION" : "ESCROW PROTECTED"}
              </span>
            </div>
          </aside>

          {/* RIGHT STAGE (CHAT & CONVERSATIONAL SPINE · 50% WIDTH ON DESKTOP · FIXED LEVEL) */}
          <section className="w-full lg:w-1/2 flex flex-col h-full min-h-0 bg-surface-container-lowest/70 border border-outline-variant/50 rounded-2xl overflow-hidden shadow-xl">
            {/* Spine Header Ribbon */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-outline-variant/50 bg-surface-container-low/90 backdrop-blur-md shrink-0">
              <div className="flex items-center gap-2.5">
                <span className="material-symbols-outlined text-[19px] text-primary">forum</span>
                <span className="font-label-md text-xs uppercase tracking-widest text-on-surface font-bold">
                  Autonomous Purchase Intelligence Stream
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-secondary shadow-[0_0_6px_#10b981]"></span>
                <span className="font-data-mono-sm text-[11px] text-on-surface-variant uppercase tracking-wider">
                  Live Concierge
                </span>
              </div>
            </div>

            {/* SCROLLABLE CHAT FEED (FOCUSED INTERNAL SCROLLING) */}
            <div
              ref={chatScrollContainerRef}
              className="flex-1 overflow-y-auto px-5 py-6 min-h-0 scroll-smooth"
            >
              <div className="narrative-spine flex flex-col gap-6">
                {messages.map((msg, idx) => (
                  <div key={idx} className="relative flex flex-col gap-3">
                    {/* Timeline Pin Indicator */}
                    <div
                      className={`absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full bg-surface border-2 ${
                        msg.sender === "buyer"
                          ? "border-outline"
                          : msg.deal_status === "agreed"
                          ? "border-secondary shadow-[0_0_8px_#10b981]"
                          : isNegotiating
                          ? "border-tertiary shadow-[0_0_8px_#fbbf24]"
                          : "border-primary shadow-[0_0_8px_#4364f7]"
                      }`}
                    />

                    {msg.sender === "buyer" ? (
                      /* Shopper Inquiry Bubble */
                      <div className="flex flex-col items-end">
                        <div className="bg-surface-container-high border border-outline-variant/60 rounded-xl px-4 py-2.5 max-w-[88%] shadow-sm">
                          <div className="flex items-center justify-between gap-4 mb-1">
                            <span className="font-label-md text-[10px] uppercase tracking-wider text-on-surface-variant font-bold">
                              Collector Query
                            </span>
                            <span className="font-data-mono-sm text-[10px] text-outline">{msg.time || "10:14 AM"}</span>
                          </div>
                          <p className="font-body-md text-[14px] text-on-surface font-medium">
                            &quot;{msg.text}&quot;
                          </p>
                        </div>
                      </div>
                    ) : (
                      /* AURA Concierge Evidentiary Response */
                      <div className="flex flex-col gap-2.5 bg-surface-container-lowest border border-outline-variant/50 rounded-xl p-4 shadow-sm">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-primary shadow-[0_0_6px_#4364f7]"></span>
                            <span className="font-label-md text-xs uppercase tracking-wider text-primary font-bold">
                              AURA Confidence System
                            </span>
                          </div>
                          <span className="font-data-mono-sm text-[10px] text-on-surface-variant uppercase">
                            Visual Evidence Protocol
                          </span>
                        </div>

                        <p className="font-body-lg text-[15px] text-on-surface leading-relaxed whitespace-pre-line">
                          {msg.text}
                        </p>

                        {/* Inline Proof Block if evidence items cited */}
                        {msg.evidence_items && msg.evidence_items.length > 0 && (
                          <div className="mt-2 rounded-lg overflow-hidden border border-outline-variant/50 bg-surface-container-low">
                            <div className="w-full aspect-[16/10] overflow-hidden bg-[#12131a] relative flex items-center justify-center">
                              {msg.evidence_items[0].image_url ||
                              selectedProduct?.id === "prod_001" ||
                              selectedProduct?.id === "prod_002" ||
                              selectedProduct?.id === "prod_003" ||
                              selectedProduct?.id === "prod_004" ||
                              selectedProduct?.id === "prod_005" ||
                              selectedProduct?.id === "prod_006" ? (
                                <img
                                  alt={msg.evidence_items[0].label}
                                  className="w-full h-full object-cover"
                                  src={
                                    msg.evidence_items[0].image_url ||
                                    (selectedProduct?.id === "prod_001"
                                      ? "/images/products/prod_001/prod_001_bowl_closeup.jpg"
                                      : selectedProduct?.id === "prod_002"
                                      ? "/images/products/prod_002/prod_002_waffle_cone_evidence.png"
                                      : selectedProduct?.id === "prod_003"
                                      ? "/images/products/prod_003/prod_003_mannequin_detail.png"
                                      : selectedProduct?.id === "prod_004"
                                      ? "/images/products/prod_004/prod_004_customer_display.png"
                                      : selectedProduct?.id === "prod_005"
                                      ? "/images/products/prod_005/prod_005_weave_macro.jpg"
                                      : "/images/products/prod_006/prod_006_unwrapped_slab.png")
                                  }
                                />
                              ) : (
                                <CeramicVaseIllustration plate="workshop" />
                              )}
                            </div>
                            <div className="px-3.5 py-2 bg-[#131726] border-t border-primary/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                              <div className="flex items-center gap-2 text-primary">
                                <span className="material-symbols-outlined text-[16px]">verified</span>
                                <span className="font-data-mono-sm text-[11px] font-semibold tracking-wide uppercase">
                                  Cited in AURA Evidence Dossier · {msg.evidence_items[0].label}
                                </span>
                              </div>
                              <span className="font-data-mono-sm text-[10px] text-primary/80 uppercase">
                                Evidence Record Verified
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}



                {/* STAGE 4: VALIDATED DEAL CERTIFICATE (IN CHAT DOSSIER SUMMARY) */}
                {isDealAgreed && activeDeal && (
                  <div className="relative flex flex-col gap-3">
                    {/* Timeline Pin (Emerald) */}
                    <div className="absolute -left-[31px] top-2 w-3.5 h-3.5 rounded-full bg-surface border-2 border-secondary shadow-[0_0_8px_#10b981]"></div>

                    <div className="flex flex-col bg-surface-container-lowest border-2 border-secondary/40 rounded-xl shadow-lg overflow-hidden">
                      {/* Security Stamp Ribbon */}
                      <div className="h-1.5 w-full bg-secondary shadow-[0_0_10px_#10b981]"></div>

                      <div className="p-4 flex flex-col gap-3.5">
                        {/* Certificate Header */}
                        <div className="flex items-center justify-between pb-2.5 border-b border-outline-variant/40">
                          <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-[18px] text-secondary">verified_user</span>
                            <span className="font-data-mono-sm text-xs uppercase font-bold tracking-wider text-on-surface">
                              Validated Deal Certificate #{activeDeal.validation_code || "AF-9982"}
                            </span>
                          </div>
                          <span className="font-data-mono-sm text-[10px] text-secondary font-bold uppercase bg-secondary-container/40 border border-secondary/40 px-2 py-0.5 rounded">
                            Negotiation Finalized
                          </span>
                        </div>

                        {/* Acquisition Title */}
                        <div className="flex justify-between items-start">
                          <div>
                            <h2 className="font-headline-lg text-lg text-on-surface">Acquisition Dossier Agreed</h2>
                            <p className="font-body-sm text-[11px] text-on-surface-variant mt-0.5">
                              {selectedProduct?.name} · {activeDeal.quantity} Unit Suite (Batch No. {selectedProduct?.id.replace("prod_", "") || "04"})
                            </p>
                          </div>
                          <div className="text-right">
                            <span className="font-label-md text-[10px] uppercase tracking-widest text-on-surface-variant block">
                              Payable
                            </span>
                            <span className="font-data-mono-sm text-sm font-bold text-secondary">
                              ₹{formatCurrency(activeDeal.total_payable_amount)}
                            </span>
                          </div>
                        </div>

                        {/* Ledger Breakdown */}
                        <div className="flex flex-col divide-y divide-outline-variant/30 bg-surface-container-low rounded-lg px-3 py-1.5 border border-outline-variant/40 text-xs">
                          <div className="flex items-center justify-between py-1.5">
                            <span className="font-body-md text-on-surface">
                              {activeDeal.quantity} × {selectedProduct?.name} (@ ₹{formatCurrency(activeDeal.effective_unit_price)})
                            </span>
                            <span className="font-data-mono font-semibold text-on-surface tabular-nums">
                              ₹{formatCurrency(activeDeal.total_payable_amount)}
                            </span>
                          </div>

                          <div className="flex items-center justify-between py-1.5 text-on-surface-variant">
                            <div className="flex items-center gap-1.5">
                              <span className="material-symbols-outlined text-[14px] text-secondary">gavel</span>
                              <span>Deal Terms Protection &amp; Packaging</span>
                            </div>
                            <span className="font-data-mono-sm text-[11px] text-secondary font-bold uppercase">Included</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={chatEndRef} />
              </div>
            </div>

            {/* PERSISTENT CONVERSATIONAL INPUT BAR */}
            <div className="p-3 border-t border-outline-variant/50 bg-surface-container-low/95 backdrop-blur-md shrink-0">
              <div className="flex items-center gap-2 bg-surface-container-lowest p-1.5 rounded-xl border border-outline-variant/60 shadow-inner">
                <div className="w-7 h-7 rounded-lg bg-surface-container flex items-center justify-center shrink-0 text-primary">
                  <span className="material-symbols-outlined text-[16px]">neurology</span>
                </div>
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
                  placeholder="Ask AURA about provenance, logistics, or propose terms (e.g. 'Can I get under 1900?')..."
                  className="w-full bg-transparent border-none text-xs md:text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:ring-0 focus:outline-none px-1"
                />
                <button
                  onClick={() => handleSendMessage()}
                  disabled={isSending || !inputText.trim()}
                  className="bg-primary hover:bg-primary-container text-on-primary px-3 py-1.5 rounded-lg font-label-md text-xs uppercase font-semibold flex items-center gap-1 shrink-0 transition-all cursor-pointer disabled:opacity-40 shadow-xs"
                >
                  <span>{isSending ? "..." : "Send"}</span>
                  <span className="material-symbols-outlined text-[14px]">arrow_upward</span>
                </button>
              </div>
            </div>

            {/* RAZORPAY PAYMENT SECTION (APPEARS BELOW CHAT UPON FINAL ROUND / DEAL AGREED) */}
            {isDealAgreed && activeDeal && (
              <div className="p-4 border-t-2 border-secondary/50 bg-[#0d1714] shrink-0 animate-fadeIn">
                <div className="flex flex-col gap-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-[18px] text-secondary">lock</span>
                      <h3 className="font-label-md text-xs uppercase font-bold tracking-wider text-on-surface">
                        Now make a secure payment through Razorpay
                      </h3>
                    </div>
                    <span className="font-data-mono-sm text-xs font-bold text-secondary bg-secondary-container/40 border border-secondary/40 px-2 py-0.5 rounded">
                      Total: ₹{formatCurrency(activeDeal.total_payable_amount)}
                    </span>
                  </div>

                  {!orderResult ? (
                    <div className="flex flex-col gap-2">
                      <button
                        onClick={handleProceedToPayment}
                        disabled={isPaymentProcessing}
                        className="w-full bg-white hover:bg-[#eae7e7] text-black py-3 px-4 rounded-lg flex items-center justify-center gap-2.5 active:scale-[0.99] transition-all cursor-pointer shadow-md disabled:opacity-50 font-bold"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          {isPaymentProcessing ? "progress_activity" : "fingerprint"}
                        </span>
                        <span className="font-label-md text-xs md:text-sm uppercase tracking-wider">
                          {paymentStep === 1
                            ? "Preparing Escrow Protection..."
                            : paymentStep === 2
                            ? "Securing Razorpay Order..."
                            : paymentStep === 3
                            ? "Verifying Payment Signature..."
                            : `Pay ₹${formatCurrency(activeDeal.total_payable_amount)} with Razorpay`}
                        </span>
                      </button>

                      <div className="flex items-center justify-center gap-1.5 text-[11px] text-on-surface-variant">
                        <span className="material-symbols-outlined text-[14px] text-secondary">shield</span>
                        <span>Official Razorpay Gateway · Deal terms escrow protection</span>
                      </div>

                      {orderError && (
                        <p className="text-xs text-red-400 text-center font-medium">
                          ⚠️ {orderError}
                        </p>
                      )}
                    </div>
                  ) : verifiedPayment ? (
                    /* Verified Payment & Escrow Reserved State */
                    <div className="flex flex-col gap-2.5 animate-fadeIn">
                      <div className="w-full bg-secondary text-[#022c22] py-2.5 px-4 rounded-lg flex items-center justify-center gap-2 shadow-sm font-bold text-xs">
                        <span className="material-symbols-outlined text-[18px]">verified_user</span>
                        <span>Payment Captured &amp; Escrow Reserved · ₹{formatCurrency(verifiedPayment.total_payable_amount ?? activeDeal?.total_payable_amount ?? 0)}</span>
                      </div>

                      <div className="bg-surface-container-low p-3 rounded-lg border border-secondary/40 text-[11px] flex flex-col gap-2">
                        <div className="flex justify-between items-center">
                          <span className="text-on-surface-variant">Payment Status: </span>
                          <span className="font-data-mono font-bold text-secondary uppercase tracking-wider">
                            {verifiedPayment.payment_status}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-on-surface-variant">Payment ID: </span>
                          <span className="font-data-mono font-semibold text-secondary">{verifiedPayment.payment_id}</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-on-surface-variant">Razorpay Order ID: </span>
                          <span className="font-data-mono font-semibold text-on-surface">{verifiedPayment.order_id}</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-on-surface-variant">Escrow Status: </span>
                          <span className="font-data-mono font-bold text-secondary uppercase tracking-wider">
                            {verifiedPayment.escrow_status} (Deal Terms Escrow Hold)
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-on-surface-variant">Effective Rate: </span>
                          <span className="font-data-mono text-on-surface">
                            ₹{formatCurrency(verifiedPayment.effective_unit_price ?? activeDeal?.effective_unit_price ?? 0)} / unit ({verifiedPayment.quantity ?? activeDeal?.quantity ?? 1} {(verifiedPayment.quantity ?? activeDeal?.quantity ?? 1) === 1 ? "unit" : "units"})
                          </span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    /* Order Created State */
                    <div className="flex flex-col gap-2 animate-fadeIn">
                      <div className="w-full bg-surface-container-high text-on-surface py-2.5 px-4 rounded-lg flex items-center justify-center gap-2 border border-outline-variant/60 shadow-sm font-bold text-xs">
                        <span className="material-symbols-outlined text-[18px] text-primary animate-spin">progress_activity</span>
                        <span>Order Created · Awaiting Payment Verification #{orderResult.order_id}</span>
                      </div>

                      <div className="bg-surface-container-low p-2.5 rounded border border-outline-variant/40 text-[11px] flex justify-between">
                        <div>
                          <span className="text-on-surface-variant">Order ID: </span>
                          <span className="font-data-mono font-semibold text-on-surface">{orderResult.order_id}</span>
                        </div>
                        <div>
                          <span className="text-on-surface-variant">Receipt: </span>
                          <span className="font-data-mono text-on-surface">{orderResult.receipt}</span>
                        </div>
                        <div>
                          <span className="text-on-surface-variant">Status: </span>
                          <span className="font-data-mono text-secondary font-bold uppercase">ORDER CREATED</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
