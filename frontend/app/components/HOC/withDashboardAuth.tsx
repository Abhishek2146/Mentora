import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";

export function withDashboardAuth(WrappedComponent: React.ComponentType) {
  return function AuthenticatedComponent(props: any) {
    const router = useRouter();
    const { isAuthenticated, checkAuth } = useAuthStore();

    useEffect(() => {
      checkAuth();
      if (!isAuthenticated) {
        router.push("/login");
      }
    }, [isAuthenticated, checkAuth, router]);

    if (!isAuthenticated) {
      return null;
    }

    return <WrappedComponent {...props} />;
  };
}
