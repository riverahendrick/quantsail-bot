import { useEffect, useState } from "react";
import { auth } from "@/lib/firebase";
import { User, signInWithEmailAndPassword, updatePassword, createUserWithEmailAndPassword } from "firebase/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslations } from "next-intl";
import { DASHBOARD_CONFIG } from "@/lib/config";
import { listUsers } from "@/lib/api";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  // Demo mode: skip auth entirely so the dashboard is browsable without Firebase
  if (DASHBOARD_CONFIG.DEMO_MODE) {
    return <>{children}</>;
  }


  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [requiresPasswordChange, setRequiresPasswordChange] = useState(false);
  const [isOwnerSetup, setIsOwnerSetup] = useState(false);
  const [systemChecked, setSystemChecked] = useState(false);

  const tAuth = useTranslations("Auth");

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((u) => {
      setUser(u);
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  // Check if system has any users
  useEffect(() => {
    const checkSystemUsers = async () => {
      if (systemChecked || DASHBOARD_CONFIG.USE_MOCK_DATA) {
        setSystemChecked(true);
        return;
      }

      // If there's already a Firebase user logged in, skip owner setup
      if (user) {
        setSystemChecked(true);
        return;
      }

      try {
        const users = await listUsers();
        if (users.length === 0) {
          setIsOwnerSetup(true);
        }
      } catch {
        // If API is not available, don't force owner setup - let Firebase handle it
        console.log("API not available, Firebase auth will handle user management");
        setIsOwnerSetup(false);
      } finally {
        setSystemChecked(true);
      }
    };

    checkSystemUsers();
  }, [systemChecked, user]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Real Firebase authentication only
      const result = await signInWithEmailAndPassword(auth, email, password);

      // Check if this is first-time login (requires password change)
      // This would be determined by a custom claim or user metadata from your backend
      const userMetadata = result.user.metadata;
      const isFirstLogin = !userMetadata.lastSignInTime || userMetadata.creationTime === userMetadata.lastSignInTime;

      if (isFirstLogin) {
        setRequiresPasswordChange(true);
      }
    } catch (err: unknown) {
      // Cast to any to check for firebase specific properties safely
      const fbError = err as { code?: string; message?: string };

      if (fbError.code === 'auth/api-key-not-authorized' || fbError.code === 'auth/operation-not-allowed') {
        // Firebase not properly configured - show clear error message
        setError("Firebase not properly configured. Please check your Firebase project settings and enable Email/Password authentication.");
      } else if (fbError.message) {
        setError(fbError.message);
      } else {
        setError("Unknown error");
      }
    }
  };

  const handleOwnerRegistration = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Create owner account in Firebase only
      const result = await createUserWithEmailAndPassword(auth, email, password);

      // For now, we'll consider the owner registered
      // In production, you'd also call your API to create the user with OWNER role
      setIsOwnerSetup(false);
      setUser(result.user);
    } catch (err: unknown) {
      // Cast to any to check for firebase specific properties safely
      const fbError = err as { code?: string; message?: string };

      if (fbError.code === 'auth/api-key-not-authorized' || fbError.code === 'auth/operation-not-allowed') {
        // Firebase not properly configured - show clear error message
        setError("Firebase not properly configured. Please check your Firebase project settings and enable Email/Password authentication.");
      } else if (fbError.message) {
        setError(fbError.message);
      } else {
        setError("Failed to create owner account");
      }
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const form = e.target as HTMLFormElement;
      const newPassword = (form.elements.namedItem('new-password') as HTMLInputElement).value;
      const confirmPassword = (form.elements.namedItem('confirm-password') as HTMLInputElement).value;

      if (newPassword !== confirmPassword) {
        setError("Passwords do not match");
        return;
      }

      if (newPassword.length < 8) {
        setError("Password must be at least 8 characters");
        return;
      }

      // Update password in Firebase
      if (auth.currentUser) {
        await updatePassword(auth.currentUser, newPassword);
      }

      // Clear password change requirement
      setRequiresPasswordChange(false);
      setPassword("");
      setError("");
    } catch (err: unknown) {
      const fbError = err as { code?: string; message?: string };
      if (fbError.message) {
        setError(fbError.message);
      } else {
        setError("Failed to update password");
      }
    }
  };

  if (loading) return <div className="flex h-screen items-center justify-center">{tAuth("loading")}</div>;

  // Owner Setup Mode - One-time registration for system owner
  if (isOwnerSetup && !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>{tAuth("ownerSetupTitle")}</CardTitle>
            <p className="text-sm text-gray-600">{tAuth("ownerSetupDescription")}</p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleOwnerRegistration} className="space-y-4">
              <div>
                <input
                  type="email"
                  placeholder={tAuth("emailPlaceholder")}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded border p-2"
                  data-testid="owner-email-input"
                />
              </div>
              <div>
                <input
                  type="password"
                  placeholder={tAuth("passwordPlaceholder")}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded border p-2"
                  data-testid="owner-password-input"
                />
              </div>
              {error && <div className="text-sm text-red-500">{error}</div>}
              <button
                type="submit"
                className="w-full rounded bg-green-600 p-2 text-white hover:bg-green-700"
                data-testid="owner-register-btn"
              >
                {tAuth("createOwnerAccount")}
              </button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (requiresPasswordChange) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>{tAuth("changePasswordTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-600 mb-4">{tAuth("changePasswordDescription")}</p>
            <form onSubmit={handlePasswordChange} className="space-y-4">
              <div>
                <input
                  type="password"
                  name="new-password"
                  placeholder={tAuth("newPasswordPlaceholder")}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded border p-2"
                  data-testid="new-password-input"
                />
              </div>
              <div>
                <input
                  type="password"
                  name="confirm-password"
                  placeholder={tAuth("confirmPasswordPlaceholder")}
                  className="w-full rounded border p-2"
                  data-testid="confirm-password-input"
                />
              </div>
              {error && <div className="text-sm text-red-500">{error}</div>}
              <button
                type="submit"
                className="w-full rounded bg-blue-600 p-2 text-white hover:bg-blue-700"
                data-testid="change-password-btn"
              >
                {tAuth("changePassword")}
              </button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>{tAuth("title")}</CardTitle>
            <p className="text-sm text-gray-600">{tAuth("accessRestricted")}</p>
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
            <div className="mt-4 text-center">
              <p className="text-xs text-gray-500">{tAuth("contactAdmin")}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
}