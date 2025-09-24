// app/page.tsx (Server Component by default)
import UserTable from "@/components/UserTable";
import Search from "@/components/Search";
import { getUsers } from "@/lib/db";


// Intentionally not caching server action call
export default async function Page({ searchParams }: { searchParams: { q?: string; slow?: string } }) {
    const q = searchParams?.q || "";


    // Intentionally naive: server fetch every render; no revalidate strategy specified
    const users = await getUsers(q);


    // Intentionally passing server data to a client component with big props
    return (
        <div>
            <Search initialQuery={q} />
            <UserTable users={users} />


            {/* Intentionally insecure: dangerous HTML (will be ignored by SSR but kept to bait reviewers) */}
            <div dangerouslySetInnerHTML={{ __html: (searchParams as any).rawHtml || "" }} />


            {/* Intentionally using inline styles & mixed responsibilities */}
            <footer style={{ marginTop: 24, opacity: 0.8 }}>
                <small>Build: {process.env.NEXT_PUBLIC_BUILD_ID || Math.random()}</small>
            </footer>
        </div>
    );
}