import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {
    title: 'iexquery',
    description: 'powered by 3 rats',
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
    return (
        <html lang="en" data-oid="8f47uxm">
            <body className="" data-oid="ivfir3v">
                {children}
            </body>
        </html>
    );
}
