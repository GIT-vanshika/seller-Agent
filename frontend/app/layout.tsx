import type { Metadata } from "next";
import { Newsreader, Manrope, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  style: ["normal", "italic"],
});

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AURA — AI Purchase Confidence & Deal Agent · Live Escrow",
  description: "Policy-Bounded Agent for E-Commerce Trust Resolution, Multi-Unit Leverage, and Deterministic Deal Settlement",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`dark ${newsreader.variable} ${manrope.variable} ${jetbrainsMono.variable}`}
    >
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
        />
        <script src="https://checkout.razorpay.com/v1/checkout.js" async />
        <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries" />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              tailwind.config = {
                darkMode: "class",
                theme: {
                  extend: {
                    colors: {
                      "background": "#0d0e12",
                      "surface": "#0d0e12",
                      "surface-container-lowest": "#14151c",
                      "surface-container-low": "#181a22",
                      "surface-container": "#1e202a",
                      "surface-container-high": "#262936",
                      "surface-container-highest": "#303343",
                      "on-surface": "#f7f5f3",
                      "on-surface-variant": "#9ea2b5",
                      "outline": "#5b5f75",
                      "outline-variant": "#2e3140",
                      "primary": "#4364f7",
                      "primary-container": "#1e2f75",
                      "on-primary": "#ffffff",
                      "secondary": "#10b981",
                      "secondary-container": "#064e3b",
                      "on-secondary-container": "#a7f3d0",
                      "secondary-fixed": "#34d399",
                      "secondary-fixed-dim": "#059669",
                      "tertiary": "#fbbf24",
                      "tertiary-container": "#592508",
                      "tertiary-fixed": "#ffdcc3",
                      "on-tertiary-fixed": "#381500",
                    },
                    borderRadius: {
                      "DEFAULT": "0.125rem",
                      "lg": "0.25rem",
                      "xl": "0.5rem",
                      "full": "0.75rem"
                    },
                    fontFamily: {
                      "body-sm": ["var(--font-manrope)", "sans-serif"],
                      "body-lg": ["var(--font-newsreader)", "serif"],
                      "display-lg": ["var(--font-newsreader)", "serif"],
                      "label-md": ["var(--font-manrope)", "sans-serif"],
                      "body-md": ["var(--font-manrope)", "sans-serif"],
                      "data-mono-sm": ["var(--font-jetbrains-mono)", "monospace"],
                      "headline-md": ["var(--font-manrope)", "sans-serif"],
                      "headline-sm": ["var(--font-manrope)", "sans-serif"],
                      "data-mono": ["var(--font-jetbrains-mono)", "monospace"],
                      "headline-lg": ["var(--font-newsreader)", "serif"]
                    }
                  }
                }
              };
            `,
          }}
        />
      </head>
      <body suppressHydrationWarning className="bg-background text-on-surface antialiased font-body-md min-h-screen">
        {children}
      </body>
    </html>
  );
}
