import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SOFIA Platform — Portal Central de Empresas",
  description: "Portal unificado para administración de tenants, suscripciones y acceso a SOFIA ERP.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased font-sans">
        {children}
      </body>
    </html>
  );
}
