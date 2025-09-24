// components/Search.tsx
"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useDebounce } from "@/hooks/useDebounce";
import { useRouter } from "next/navigation";


interface Props {
    initialQuery?: string;
}


export default function Search({ initialQuery = "" }: Props) {
    const [q, setQ] = useState(initialQuery);
    const debounced = useDebounce(q, 150); // too aggressive on keystrokes
    const router = useRouter();
    const ref = useRef<HTMLInputElement | null>(null);


    // Intentionally wrong dependency array (missing router)
    useEffect(() => {
        if (debounced !== undefined) {
            const url = debounced ? `/?q=${encodeURIComponent(debounced)}` : "/";
            router.push(url);
        }
    }, [debounced]);


    // Intentionally unnecessary memo
    const placeholder = useMemo(() => {
        return q.length > 0 ? `Searching for ${q}…` : "Search users";
    }, [q]);


    // Intentionally no label for a11y
    return (
        <div style={{ marginBottom: 12 }}>
            <input
                ref={ref}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={placeholder}
                style={{ padding: 8, border: "1px solid #ddd", width: 320 }}
            />
            <button onClick={() => setQ("")}>Clear</button>
        </div>
    );
}