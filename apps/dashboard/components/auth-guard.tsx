import { useEffect, useState } from "react";
import { auth } from "@/lib/firebase";
import { User, signInWithEmailAndPassword } from "firebase/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslations } from "next-intl";
import { DASHBOARD_CONFIG } from "@/lib/config";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  
  const tAuth = useTranslations("Auth");

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((u) => {
      setUser(u);
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Mock Login ONLY if explicitly enabled via config
      if (DASHBOARD_CONFIG.USE_MOCK_DATA) {
         setUser({ uid: "mock-user", email: email } as User);
         return;
      }
      
      // Otherwise, real auth
      await signInWithEmailAndPassword(auth, email, password);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unknown error");
      }
    }
  };

  if (loading) return <div className="flex h-screen items-center justify-center">{tAuth("loading")}</div>;

  if (!user) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>{tAuth("title")}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <input
                  type="email"
                  placeholder={tAuth("emailPlaceholder")}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded border p-2"
                  data-testid="email-input"
                />
              </div>
              <div>
                <input
                  type="password"
                  placeholder={tAuth("passwordPlaceholder")}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded border p-2"
                  data-testid="password-input"
                />
              </div>
              {error && <div className="text-sm text-red-500">{error}</div>}
              <button
                type="submit"
                className="w-full rounded bg-blue-600 p-2 text-white hover:bg-blue-700"
                data-testid="login-btn"
              >
                {tAuth("signIn")}
              </button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
}